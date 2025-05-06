# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models
from odoo.tools import SQL

from ..orm.field_vector import Vector
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
    embedding_vector = Vector(size=1536)
    _embedding_vector_idx = models.Index("USING ivfflat (embedding_vector vector_cosine_ops)")

    @api.model
    def _get_similar_chunks(self, query_embedding, attachment_ids, top_n=5):
        if not attachment_ids:
            return self
        # Execute the SQL query to find similar embeddings within the specified attachments
        return self.browse(id_ for id_, *_ in self.env.execute_query(SQL(
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
        )

    @api.model
    def _cron_generate_embedding(self, batch_size=100):
        missing_embeddings = self.env["ai.embedding"].search([("embedding_vector", "=", False)], limit=batch_size)

        _logger.info("Starting embedding update - missing %s embeddings.", len(missing_embeddings))

        self.env['ir.cron']._commit_progress(remaining=len(missing_embeddings))
        for embedding in missing_embeddings:
            _logger.info("Computing embedding for record %s, content length: %s", embedding.id, len(embedding.content or ""))
            response = LLMApiService(env=self.env, provider='openai').get_embedding(input=embedding.content)
            embedding.embedding_vector = response['data'][0]['embedding']
            if not self.env['ir.cron']._commit_progress(1):
                break

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
