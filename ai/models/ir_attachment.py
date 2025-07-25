# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import contextlib
import io
import logging
import re

from odoo import models
from odoo.addons.ai.models.models import AI_SUPPORTED_IMG_TYPES
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter, to_pdf_stream, PdfReadError

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    AI_MAX_PDF_PAGES = 5

    def _compute_pdf_content(self):
        """Compute the content of the PDF attachment."""
        self.ensure_one()
        if not self.raw or not self.raw.startswith(b'%PDF-'):
            return None
        try:
            from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter  # noqa: PLC0415
            from pdfminer.converter import TextConverter  # noqa: PLC0415
            from pdfminer.layout import LAParams  # noqa: PLC0415
            from pdfminer.pdfpage import PDFPage  # noqa: PLC0415
            logging.getLogger("pdfminer").setLevel(logging.CRITICAL)
        except ImportError:
            return None

        f = io.BytesIO(self.raw)
        resource_manager = PDFResourceManager()
        laparams = LAParams(
            line_margin=0.5,
            char_margin=2.0,
            word_margin=0.1,
            boxes_flow=0.5,
            detect_vertical=True,
        )

        with io.StringIO() as content, TextConverter(
            resource_manager,
            content,
            laparams=laparams
        ) as device:
            interpreter = PDFPageInterpreter(resource_manager, device)
            for page in PDFPage.get_pages(f):
                interpreter.process_page(page)

            buf = content.getvalue()

        return self._clean_pdf_content(buf)

    def _clean_pdf_content(self, buf):
        """
        Clean the PDF content by removing unwanted characters and formatting.
        """
        buf = buf.replace('\r\n', '\n').replace('\r', '\n')
        paragraphs = re.split(r'\n\s*\n', buf)
        paragraphs = [re.sub(r'[ \t]+', ' ', p.strip()) for p in paragraphs]
        return '\n'.join(paragraphs)

    def _generate_embedding(self, embedding_model):
        self.ensure_one()
        content = self._compute_pdf_content()
        chunks = self._chunk_text(content if content else self.index_content)
        vals_list = []
        for chunk in chunks:
            if self.name:
                chunk = f"Attachment Name: {self.name}\n{chunk}"
            vals_list.append({
                'attachment_id': self.id,
                'content': chunk,
                'embedding_model': embedding_model,
            })

        self.env['ai.embedding'].create(vals_list)

    @staticmethod
    def _clean_text(text):
        """
        Clean up the text content while preserving meaningful structure.

        :param str text: Raw text content to clean
        :returns: Cleaned text content
        :rtype: str
        """
        text = text.replace('\r\n', '\n')

        # Split into lines and process
        lines = text.split('\n')
        result = []
        current_paragraph = []

        for line in lines:
            stripped = line.strip()

            if not stripped:
                if current_paragraph:
                    result.append(' '.join(current_paragraph))
                    current_paragraph = []
                continue

            if stripped.endswith(':') or (len(stripped) < 120 and stripped.endswith('.')):
                if current_paragraph:
                    result.append(' '.join(current_paragraph))
                    current_paragraph = []
                result.append(stripped)
                continue

            current_paragraph.append(stripped)

        if current_paragraph:
            result.append(' '.join(current_paragraph))

        # Join with single newlines between paragraphs
        text = '\n'.join(result)

        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)
        return text.strip()

    @staticmethod
    def _chunk_text(text, chunk_size=1500, margin=200, min_chunk_size=500):
        """
        Split text into chunks based on character count with a margin to avoid abrupt cuts.

        :param str text: The input text to chunk.
        :param int chunk_size: Target chunk size in characters.
        :param int margin: Allow flexibility in chunk sizes within chunk_size ± margin.
        :param int min_chunk_size: Minimum size a chunk should have before finalizing.
        :return: List of text chunks
        :rtype: list[str]
        """
        cleaned_text = IrAttachment._clean_text(text)
        chunks = []
        paragraphs = cleaned_text.split('\n')

        current_chunk = []
        current_length = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue  # Skip empty lines

            para_length = len(para)

            # If current chunk is too small, try to merge with the next one
            if current_chunk and (current_length + para_length <= chunk_size + margin):
                current_chunk.append(para)
                current_length += para_length + 1  # Account for spaces
                continue

            # If the current chunk is large enough, store it
            if current_length >= chunk_size - margin:
                chunks.append(" ".join(current_chunk))
                current_chunk = [para]  # Start a new chunk
                current_length = para_length
            else:
                # If chunk is too small but para itself is too big, split it
                if para_length > chunk_size:
                    sentences = re.split(r'(?<=[.!?])\s+', para)
                    temp_chunk = []
                    temp_length = 0

                    for sentence in sentences:
                        sent_length = len(sentence)

                        if temp_length + sent_length > chunk_size:
                            if temp_chunk:
                                chunks.append(" ".join(temp_chunk))
                            temp_chunk = [sentence]
                            temp_length = sent_length
                        else:
                            temp_chunk.append(sentence)
                            temp_length += sent_length + 1

                    if temp_chunk:
                        chunks.append(" ".join(temp_chunk))
                else:
                    current_chunk.append(para)
                    current_length += para_length + 1

        # Merge last chunk if it's too small
        if current_chunk:
            if chunks and len(" ".join(current_chunk)) < min_chunk_size:
                chunks[-1] += " " + " ".join(current_chunk)  # Merge with previous chunk
            else:
                chunks.append(" ".join(current_chunk))

        return chunks

    def _ai_format(self, files_dict):
        vals = []
        for attachment in self:
            if attachment.checksum in files_dict:
                vals.append({'id': attachment.id, 'file': files_dict[attachment.checksum]['file_ref']})
                continue
            file_ref = f'<file_#{len(files_dict) + 1}>'
            extension = attachment.mimetype.split('/')[-1]
            if extension == 'pdf' and not attachment.url:
                # Extract the X first / last pages of the PDFs
                reader = None
                with contextlib.suppress(PdfReadError):
                    reader = OdooPdfFileReader(to_pdf_stream(attachment), strict=False)
                if not reader or reader.numPages <= self.AI_MAX_PDF_PAGES:
                    b64_datas = attachment.datas.decode()
                else:
                    writer = OdooPdfFileWriter()
                    start_pages = self.AI_MAX_PDF_PAGES // 2
                    end_pages = self.AI_MAX_PDF_PAGES - start_pages
                    for p in (*range(start_pages), *range(reader.numPages - end_pages, reader.numPages)):
                        writer.addPage(reader.getPage(p))
                    out_buff = io.BytesIO()
                    writer.write(out_buff)
                    b64_datas = base64.b64encode(out_buff.getvalue()).decode()

                files_dict[attachment.checksum] = {
                    'mimetype': 'application/pdf',
                    'value': b64_datas,
                    'file_ref': file_ref,
                }
            elif extension in AI_SUPPORTED_IMG_TYPES and not attachment.url:
                files_dict[attachment.checksum] = {
                    'mimetype': attachment.mimetype,
                    'value': attachment.datas.decode(),
                    'file_ref': file_ref,
                }
            else:
                if not attachment.index_content or attachment.index_content == "application":
                    continue
                files_dict[attachment.checksum] = {
                    'mimetype': 'text/plain',
                    'value': attachment.index_content,
                    'file_ref': file_ref
                }
            vals.append({'id': attachment.id, 'file': file_ref})
        return vals
