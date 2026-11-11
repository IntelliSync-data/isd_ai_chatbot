# AI Chatbot (isd_ai_chatbot)

Chatbot cho Odoo 18. Bot trả lời từ tài liệu và bảng hỏi đáp của khách hàng, thu lead, giao cho nhân viên, đẩy vào CRM và đặt lịch họp.

Module này kết hợp hai module cũ:
- `chatbot_ai_rag`: trả lời từ tài liệu có trích dẫn, gọi Gemini/OpenAI.
- `isd_chatbot`: lead, CRM, lịch họp, Zalo, Messenger, nút liên hệ, REST API.

Không có nội dung nào viết cứng cho một khách hàng. Giá, hotline và câu trả lời mẫu đều nằm trong dữ liệu. Muốn có sẵn một bộ ví dụ thì bấm **Nạp dữ liệu mẫu Bloompod**.

## Cách bot trả lời

Bot thử lần lượt theo thứ tự sau và dừng ở bước đầu tiên có kết quả:

1. **Hỏi đáp**: câu hỏi chứa từ khoá của một mục thì bot trả đúng nguyên văn câu trả lời của mục đó. Nếu nhiều mục cùng khớp, cụm từ khoá dài nhất thắng.
2. **Kho tri thức**: tài liệu được chia theo các tiêu đề `##`. Bot chấm điểm từng đoạn theo từ khớp, có cộng điểm khi khớp cụm hai từ, rồi trả lời kèm trích dẫn `[1]`, `[2]`.
3. **AI (Gemini, hoặc OpenAI khi Gemini lỗi)**: chỉ chạy khi đã nhập key. AI nhận các đoạn tài liệu tìm được, và nếu có câu hỏi đáp đã duyệt thì câu đó là chuẩn, AI không được nói khác.
4. Không có gì khớp thì bot dùng **câu khi không có câu trả lời** và mời khách để lại thông tin.

Không có key AI thì bot vẫn chạy bằng bước 1 và 2. Đây là phần "RAG không cần AI".

**Mở rộng tìm kiếm** (tab Tin nhắn) giúp câu hỏi tiếng Anh tìm được tài liệu tiếng Việt mà không cần dịch. Mỗi dòng một quy tắc:
```
price, cost, how much => gia ban uu dai
```

## Cài đặt

1. Thêm thư mục repo vào `addons_path`. Không cần cài thêm thư viện Python.
2. Cài **AI Chatbot**. Module phụ thuộc vào `website`, `crm`, `calendar` và `mail`.
3. Nếu database có OpenEduCat và Survey, module `isd_ai_chatbot_openeducat` sẽ tự cài theo (xem phần cuối).
4. Vào **AI Chatbot → Cấu hình → Cài đặt** và làm các bước sau:
   - Tab **Trợ lý**: nhập tên doanh nghiệp, giọng văn và những điều bot không được hứa.
   - Tab **Widget**: chọn website hiện bong bóng chat, màu, các nút Zalo / gọi / Messenger.
   - Tab **Khoá AI** (không bắt buộc): Gemini và/hoặc OpenAI.
   - Tab **Lead**: múi giờ của khách, tự giao lead, tự tạo lead CRM.
5. Vào **Thiết lập → Người dùng**, mở từng nhân viên nhận lead và đánh dấu **Nhận lead chatbot** (tab AI Chatbot).
6. Nhập nội dung vào **Hỏi đáp** và **Kho tri thức**. Kho tri thức nhận file .docx/.doc/.txt và giữ lại các tiêu đề Word.

### Phân quyền

| Nhóm | Được làm gì |
|---|---|
| Người dùng | Chỉ xem lead và hội thoại được giao cho mình |
| Biên tập | Sửa kho tri thức và hỏi đáp, không xem lead |
| Quản lý | Mọi lead, mọi hội thoại, cùng kho tri thức |
| Quản trị viên | Cộng thêm cài đặt, API key, Zalo/Facebook, nhật ký webhook |

## Nhúng vào trang ngoài Odoo

Website Odoo được chọn trong tab Widget tự có bong bóng chat. Trang khác thì dán đoạn mã sau, copy từ ô **Site khác**:

```html
<script src="https://<domain-odoo>/isd_ai_chatbot/widget.js" defer></script>
```

Ô **Tên miền được phép** giới hạn những site được gọi API chat. Để trống thì site nào cũng gọi được.

Widget gồm:
- Nút chính bung ra Messenger / Zalo / Gọi / Chat. Nút chỉ hiện khi có link hoặc số điện thoại.
- Khung chat có nút chuyển VI/EN, câu hỏi gợi ý, trích dẫn tài liệu và form để lại thông tin.

Hội thoại được lưu ở server. Khách tải lại trang vẫn tiếp tục được cuộc trò chuyện cũ.

## Lead

Lead được tạo khi khách để lại tên cùng số điện thoại hoặc email. Có bốn đường vào:
- trong chat, khi bot hỏi từng câu
- qua form trên widget
- qua Zalo hoặc Messenger
- qua REST API

Bot nhận ra khi khách muốn gặp người thật, ví dụ "cho tôi gặp nhân viên". Khi đang hỏi thông tin mà khách hỏi chen một câu khác, bot trả lời câu đó rồi hỏi tiếp.

Các nút trên lead:

| Nút | Tác dụng |
|---|---|
| Lưu vào CRM | Tạo `crm.lead` có đủ thông tin. Nếu lead chưa giao cho ai thì hỏi giao cho ai trước. |
| Chọn giờ họp | Nhập hoặc sửa giờ họp |
| Đặt lịch họp | Tạo sự kiện lịch có link họp Odoo Discuss và gắn vào cơ hội CRM. Gửi email cho khách (VI/EN theo ngôn ngữ của khách) và cho nhân viên. Giờ trong email tính theo múi giờ của khách. |
| Phân tích | Dùng AI (hoặc regex khi không có key) đọc tin nhắn của khách để điền tên, email, số điện thoại và giờ hẹn |
| Huỷ / Mở lại | Đổi trạng thái lead |

Lead tự giao cho người **Nhận lead chatbot** đang có ít lead mở nhất. Người được giao nhận một activity.

## Zalo OA

1. Tab **Zalo**: bật Zalo, nhập App ID, App Secret, Access Token và Refresh Token.
2. Copy **URL webhook Zalo** dán vào trang developer của OA, đăng ký sự kiện `user_send_text`.
3. Nhập **OA Secret Key (webhook)**. Khi đã nhập, mọi lời gọi không có chữ ký `X-ZEvent-Signature` hợp lệ đều bị từ chối.

Token tự làm mới khi Zalo báo hết hạn (lỗi -216). Tin nhắn do chính OA gửi (`oa_send_text`) bị bỏ qua, để bot không tự trả lời chính mình.

## Facebook Messenger

1. Tab **Facebook**: bật Facebook, nhập Page ID, Page Access Token, App ID, App Secret, và tự đặt một Verify Token.
2. Trong app Meta, mục Webhooks: callback URL là **URL webhook Facebook**, verify token giống ô ở trên. Đăng ký page nhận `messages`.

Mọi lời gọi đều được kiểm bằng `X-Hub-Signature-256` với app secret. Tin Facebook gửi lại (cùng `mid`) chỉ được trả lời một lần.

Mọi lời gọi webhook đều ghi vào **Nhật ký webhook**. Nhật ký cũ hơn 30 ngày tự xoá.

## REST API

Base URL: `https://<domain-odoo>/isd_ai_chatbot/api/v1`

Mọi API trừ tạo lead đều cần API key, tạo ở tab **API**. Gửi key bằng một trong hai header:
```
Authorization: Bearer <key>
X-API-Key: <key>
```

### Tạo lead (không cần key)

```
POST /leads
Content-Type: application/json

{
  "name": "Nguyễn Văn A",
  "phone": "0901234567",
  "email": "a@example.com",
  "topic": "Hỏi giá",
  "message": "Nội dung khách viết",
  "consultation_datetime": "2026-11-20 03:00:00",
  "source_code": "website"
}
```

- Bắt buộc có `name` và ít nhất một trong `phone` / `email`.
- `consultation_datetime` theo giờ UTC.
- Khi không có key:
  - `source_code` chỉ nhận `api`, `website` hoặc `manual`
  - không đặt được `state` và người phụ trách
  - mỗi IP chỉ tạo được 10 lead trong 10 phút
- Khi có key: được gửi thêm `state` và `assigned_user_email`.

Response `201`:
```json
{
  "success": true,
  "data": {
    "id": 12, "name": "Nguyễn Văn A", "email": "a@example.com", "phone": "0901234567",
    "topic": "Hỏi giá", "message": "Nội dung khách viết", "state": "new",
    "consultation_datetime": "2026-11-20 03:00:00", "source": "website",
    "assigned_user": "sale1@example.com", "crm_lead_id": null,
    "created": "2026-11-11 02:15:00"
  }
}
```

Lỗi `400`: `{"success": false, "errors": ["name is required", "email or phone is required"]}`

### Các API cần key

| Method | Đường dẫn | Ghi chú |
|---|---|---|
| GET | `/leads?state=new&limit=50&offset=0` | `limit` tối đa 200. Trả về `{"success", "total", "data": [...]}` |
| GET | `/leads/<id>` | |
| PUT | `/leads/<id>` | Body JSON, nhận các trường `name`, `email`, `phone`, `topic`, `message`, `note`, `consultation_datetime`, `state`, `assigned_user_email` |
| DELETE | `/leads/<id>` | |

`state` có các giá trị: `new`, `crm`, `booked`, `cancelled`. Thiếu key hoặc sai key thì trả về `401`, không có lead thì `404`.

## Module isd_ai_chatbot_openeducat

Module bridge, tự cài khi database có `openeducat_core` và `survey`.

- **Cấu hình → Liên kết khảo sát**: chọn khảo sát và câu hỏi nào nhận tên, email, số điện thoại, chủ đề của lead.
- Trên lead có nút **Mời làm học viên**. Nút này làm ba việc:
  1. tạo học viên OpenEduCat với tài khoản **portal**
  2. gửi email đặt mật khẩu
  3. mở khảo sát đã điền sẵn câu trả lời từ lead

Database không có OpenEduCat thì module chính vẫn chạy bình thường.
