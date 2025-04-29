# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import psycopg2

from odoo import api, fields, models
from odoo.tools import SQL

from ..utils.llm_api_service import LLMApiService

_logger = logging.getLogger(__name__)


class AIEmbedding(models.Model):
    _name = 'ai.embedding'
    _description = "Attachment Chunks Embedding"
    _order = 'sequence'

    attachment_id = fields.Many2one(
        'ir.attachment',
        string="Attachment",
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string="Sequence", default=10)
    content = fields.Text(string="Chunk Content", required=True)

    def _auto_init(self):
        super()._auto_init()

        try:
            self.env.cr.execute(SQL("CREATE EXTENSION IF NOT EXISTS vector"))
        except psycopg2.Error:
            _logger.warning("PostgreSQL extension 'vector' is required to enable RAG for AI agents")
            return

        # Add vector column if it doesn't exist
        self.env.cr.execute(SQL(
            '''
                SELECT EXISTS (
                    SELECT FROM information_schema.columns
                    WHERE table_name = 'ai_embedding'
                    AND column_name = 'embedding_vector'
                )
            ''')
        )
        exists = self.env.cr.fetchone()[0]
        if not exists:
            self.env.cr.execute(SQL("ALTER TABLE ai_embedding ADD embedding_vector vector(1536)"))

        # Create vector similarity search index
        self.env.cr.execute(SQL(
            '''
                CREATE INDEX IF NOT EXISTS ai_embedding_vector_idx
                ON ai_embedding
                USING ivfflat (embedding_vector vector_cosine_ops)
            ''')
        )

    @api.model
    def _get_similar_chunks(self, query_embedding, attachment_ids, top_n=5):

        if not attachment_ids:
            return self

        try:
            # Execute the SQL query to find similar embeddings within the specified attachments
            self.env.cr.execute(SQL(
                '''
                    SELECT
                        id,
                        1 - (embedding_vector <=> %s::vector) AS similarity
                    FROM ai_embedding
                    WHERE attachment_id = ANY(%s)
                    ORDER BY similarity DESC
                    LIMIT %s;
                ''',
                query_embedding, attachment_ids, top_n)
            )
        except psycopg2.Error:
            _logger.warning("PostgreSQL extension 'vector' is required to enable RAG for AI agents")
            return
        result_ids = [row[0] for row in self.env.cr.fetchall()]
        return self.browse(result_ids)

    @api.model
    def _cron_generate_embedding(self, batch_size=100):
        try:
            self.env.cr.execute(SQL("SELECT COUNT(id) FROM ai_embedding WHERE embedding_vector IS NULL"))
        except psycopg2.Error:
            _logger.warning("PostgreSQL extension 'vector' is required to enable RAG for AI agents")
            return
        number_of_missing_emb = self.env.cr.fetchall()[0][0]

        _logger.info("Starting embedding update - missing %s embeddings.", number_of_missing_emb)

        if number_of_missing_emb:
            self.env.cr.execute(SQL(
                "SELECT id, content FROM ai_embedding WHERE embedding_vector IS NULL LIMIT %s",
                batch_size,
            ))
            missing_emb = self.env.cr.fetchall()
            processed_count = len(missing_emb)
            for record_id, content in missing_emb:
                _logger.info("Computing embedding for record %s, content length: %s", record_id, len(content or ""))
                response = LLMApiService(env=self.env, provider='openai').get_embedding(input=content)
                embedding = response['data'][0]['embedding']
                self.env.cr.execute(SQL(
                    "UPDATE ai_embedding SET embedding_vector = %s WHERE id = %s",
                    embedding, record_id
                ))

            self.env['ir.cron']._commit_progress(
                processed=processed_count,
                remaining=max(0, number_of_missing_emb - processed_count),
            )

    @api.autovacuum
    def _gc_embeddings(self):
        """
        Autovacuum: Cleanup embedding chunks not associated with any agent's attachments.
        """
        all_agents = self.env['ai.agent'].search([])
        used_attachment_ids = all_agents.attachment_ids + all_agents.url_attachment_ids
        if used_attachment_ids:
            unused_chunks = self.search([
                '|',
                ('attachment_id', 'not in', used_attachment_ids.ids),
                ('attachment_id', '=', False)
            ])
            if unused_chunks:
                chunk_count = len(unused_chunks)
                _logger.info("Autovacuum: Cleaning up %s unused embedding chunks", chunk_count)
                unused_chunks.unlink()
