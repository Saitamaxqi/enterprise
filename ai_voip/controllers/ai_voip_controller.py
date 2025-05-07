from odoo import http
from odoo.http import request


class AiVoipController(http.Controller):

    @http.route('/ai_voip/transcribe_call', type='http', auth='user', methods=['POST'], csrf=True)
    def transcribe_call(self, **post):
        call_id = int(post.get("voip_call_id", 0))
        recording = request.httprequest.files.get("file", False)

        if not call_id or not recording:
            return request.make_json_response({"error": "Missing VOIP call identifier or file"}, status=400)

        call = request.env["voip.call"].browse(call_id)
        if not call.exists():
            return request.make_json_response({"error": f"Call {call_id} not found"}, status=404)

        if call.user_id != request.env.user:
            return request.make_json_response({"error": "Forbidden"}, 403)
        call = call.sudo()

        call.transcription_status = "pending"

        recording_raw = recording.read()
        if len(recording_raw) > 25_000_000:
            call.transcription_status = "too_big_to_process"
            return request.make_json_response({"error": "File too large"}, status=413)

        request.env["ir.attachment"].sudo().create({
            "name": "call_recording.ogg",
            "res_model": "voip.call",
            "res_id": call.id,
            "type": "binary",
            "mimetype": "audio/ogg",
            "raw": recording_raw,
        })
        request.env.cr.commit()

        request.env.ref('ai_voip.ir_cron_transcribe_recent_voip_call').sudo()._trigger()
        return request.make_json_response({"success": True})
