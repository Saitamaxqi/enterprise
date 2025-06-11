import logging
from collections import defaultdict
from lxml import etree

from odoo.tools.mail import html_sanitize

_logger = logging.getLogger(__name__)


class HTMLTextProcessor:

    def __init__(self):
        self._parser = etree.HTMLParser(encoding='utf-8')
        self._id_registry = {}  # Maps HTML text IDs to positions

    def _parse_html(self, html_content):
        """Parse HTML content with error handling."""
        if not html_content or not html_content.strip():
            return None
        try:
            return etree.fromstring(f"<root>{html_content}</root>", self._parser)
        except etree.XMLSyntaxError as e:
            _logger.error("Invalid HTML content: %s", e)
            return None

    def extract_text_nodes(self, html_content):
        """Extract all text nodes from HTML while preserving their context."""
        tree = self._parse_html(html_content)

        if tree is None:
            return None

        dict_text = {}
        self._id_registry = {}
        sections = tree.xpath('.//section')

        """
        Website Pages in templates consist of HTML sections, which are made up of nodes.
        We need to extract the text from the nodes and group them by section.
        """
        for section_idx, section in enumerate(sections):
            self._process_node(section, dict_text, section_idx, 0)

        # Group nodes by section number
        section_groups = defaultdict(dict)
        for key, value in dict_text.items():
            section_num = key.split('-')[0]
            section_groups[section_num][key] = value

        batches = self._create_batches(section_groups)
        return batches

    def _process_node(self, node, dict_text, section_id, node_id=0):
        """Process a single node and its children recursively."""
        if node is None:
            return node_id

        # Handle text content
        if node.text and node.text.strip():
            text_id = f"s{section_id}-t{node_id}"
            dict_text[text_id] = node.text
            self._id_registry[text_id] = {
                'position': node_id,
                'type': 'text',
                'section': section_id
            }
            node_id += 1

        # Process children recursively
        for child in node:
            node_id = self._process_node(child, dict_text, section_id, node_id)

        # Handle tail content
        if node.tail and node.tail.strip():
            text_id = f"s{section_id}-t{node_id}"
            dict_text[text_id] = node.tail
            self._id_registry[text_id] = {
                'position': node_id,
                'type': 'tail',
                'section': section_id
            }
            node_id += 1

        return node_id

    def _create_batches(self, section_groups, min_batch_size=5, max_batch_size=25):
        """
        Create batches of sections ensuring each batch is between min_batch_size and max_batch_size.

        Args:
            section_groups (dict): Dictionary of sections grouped by section number
            min_batch_size (int): Minimum number of nodes in a batch
            max_batch_size (int): Maximum number of nodes in a batch

        Returns:
            list: List of batches, where each batch is a dictionary of nodes
        """
        batches = []
        current_batch = {}
        current_batch_size = 0

        for section_num in section_groups:
            section_nodes = section_groups[section_num]
            section_size = len(section_nodes)

            # If current batch is empty and section size is less than min_batch_size,
            # add it to current batch
            if not current_batch and section_size < min_batch_size:
                current_batch.update(section_nodes)
                current_batch_size += section_size
                continue

            # If adding this section would exceed max size and current batch meets minimum size,
            # start a new batch
            if current_batch_size + section_size > max_batch_size and current_batch_size >= min_batch_size:
                batches.append(current_batch)
                current_batch = {}
                current_batch_size = 0

            # Add section to current batch
            current_batch.update(section_nodes)
            current_batch_size += section_size

        # Add the last batch if it's not empty
        if current_batch:
            batches.append(current_batch)

        return batches

    def process_ai_response(self, ai_response, original_html):
        """Process AI response and update the original HTML with new text content."""
        # Parse and update HTML
        tree = self._parse_html(original_html)
        self._update_tree_text(tree, ai_response)

        # Return updated HTML
        result = etree.tostring(tree, encoding='unicode')

        return result[6:-7]  # Remove <root> and </root> tags

    def _update_tree_text(self, tree, ai_response_dict):
        """
        Iterate over the sections and update the text content in the tree
        based on AI response dictionary.
        """
        sections = tree.xpath('.//section')

        for section_idx, section in enumerate(sections):
            self._update_tree_node(section, ai_response_dict, section_idx)

    def _is_inline_tag(self, tag):
        """Return True if the tag is an inline HTML tag."""
        inline_tags = {'a', 'b', 'br', 'button', 'em', 'i', 'img', 'input', 'label', 'small', 'span', 'strong', 'u'}
        return tag in inline_tags

    def _update_tree_node(self, node, ai_response_dict, section_id=None, node_id=0):
        """Recursively update individual node text using _id_registry map."""
        if node is None:
            return node_id

        text_id = f"s{section_id}-t{node_id}"

        if text_id not in ai_response_dict:
            return node_id

        # Update text content
        if node.text and node.text.strip():
            text_id = f"s{section_id}-t{node_id}"
            if text_id in ai_response_dict:
                new_text = self._sanitize_ai_response(ai_response_dict[text_id])
                if self._is_inline_tag(node.tag):
                    new_text = ' ' + new_text
                node.text = new_text
            node_id += 1

        # Process children recursively
        for child in node:
            node_id = self._update_tree_node(child, ai_response_dict, section_id, node_id)

        # Update tail content
        if node.tail and node.tail.strip():
            text_id = f"s{section_id}-t{node_id}"
            if text_id in ai_response_dict:
                new_text = self._sanitize_ai_response(ai_response_dict[text_id])
                if len(new_text.split()[0]) > 1:
                    new_text = ' ' + new_text
                node.tail = new_text
            node_id += 1

        return node_id

    def _sanitize_ai_response(self, ai_generated_response):
        """Sanitize the AI response text for safe HTML insertion using html.escape."""
        if not isinstance(ai_generated_response, str):
            ai_generated_response = str(ai_generated_response)
        return html_sanitize(ai_generated_response).striptags()
