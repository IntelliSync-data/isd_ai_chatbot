# -*- coding: utf-8 -*-
"""The Bloompod content chatbot_ai_rag shipped hard-coded in Python.

Here it is data: loaded on demand from Settings, then edited like any other
record. Changing the price no longer means a code change and a deploy.
"""

CONFIG = {
    'business_name': 'Bloompod',
    'business_website': 'https://bloompod.vn',
    'pronoun_style': "Xưng 'em', gọi khách là 'ba/mẹ', mở đầu câu bằng 'Dạ'",
    'greeting_vi': 'Chào ba/mẹ! 👋 Cần tư vấn lộ trình nghe Bloompod cho bé 0–3 tuổi, hỏi em ngay nhé!',
    'greeting_en': 'Hi! 👋 Ask us anything about Bloompod for children aged 0–3.',
    'tone_instruction': ('Ấm áp, thấu cảm với phụ huynh có con nhỏ 0–3 tuổi, giải thích khoa học dễ hiểu, '
                         'ngắn gọn tối đa 3–4 câu mỗi lượt trả lời.'),
    'core_philosophy': ('Ngôn ngữ bắt đầu từ lắng nghe nhịp điệu (rhythm), âm sắc (tone) và cấu trúc (structure) '
                        'theo chu kỳ lặp lại. Bloompod không phải lớp học, không phải app, không màn hình, '
                        'không ép trẻ nói sớm.'),
    'forbidden_claims': ("Không cam kết 'bé nghe vài tuần là nói được tiếng Anh ngay'; không khuyên bật máy cả "
                         "ngày; không tự đưa ra giá hoặc khuyến mãi ngoài thông tin trong tài liệu."),
    'handoff_rule': ('Khi ba/mẹ hỏi mua sỉ/đại lý, kiểm tra vận đơn hoặc khiếu nại kỹ thuật, mời để lại số điện '
                     'thoại để đội ngũ hỗ trợ trực tiếp.'),
    'suggested_questions_vi': ('Giá bộ sản phẩm Bloompod Kit & ưu đãi hiện tại?\n'
                               'Bé 0–3 tuổi nghe lộ trình mỗi ngày thế nào cho hiệu quả?\n'
                               'Vì sao giá cao hơn loa nghe nhạc MP3 thông thường?\n'
                               'Chính sách bảo hành & đổi trả trong 7 ngày như thế nào?'),
    'suggested_questions_en': ("What's the price of the Bloompod Kit?\n"
                               'How should a 0–3 year old use it every day?\n'
                               'Why does it cost more than a regular speaker?\n'
                               "What's the warranty and return policy?"),
    'query_expansions': ('price, cost, how much, buy, order, discount, kit => gia ban uu dai bloompod kit dat mua\n'
                         'expensive, speaker, mp3, worth, compare => kich ban xu ly tu choi che dat cao hon loa thuong\n'
                         'bored, ignore, attention, listen, waste, unused => kich ban so mua ve be khong chiu nghe chan bo xo\n'
                         'schedule, routine, how long, all day, times, how to use, guide => huong dan su dung lo trinh nghe moi ngay\n'
                         'warranty, return, refund, shipping, delivery, address, company, contact => chinh sach bao hanh doi tra 7 ngay cong ty\n'
                         'youtube, tv, screen, app, difference => diem khac biet khong man hinh'),
}

QA = [
    {
        'name': 'Chê đắt / so với loa thường',
        'sequence': 10,
        'keywords': 'đắt\nmắc\ncao hơn loa\nloa thường\nexpensive\nspeaker\nmp3\nworth it\ncostly',
        'answer_vi': ("Dạ em rất hiểu băn khoăn của ba/mẹ ạ! Thực tế **Bloompod không phải chiếc loa MP3 ngẫu nhiên**, "
                      "mà là trọn bộ **Hệ thống Language Readiness thiết kế riêng cho não bộ bé 0–3 tuổi** "
                      "(dùng suốt 3 năm đầu đời, tính ra chỉ khoảng **1.500đ/ngày**).\n\n"
                      "* Giá ưu đãi **1.650.000đ** (giảm 300.000đ) đã gồm: máy phát lập trình chu kỳ lặp lại khoa học, "
                      "bộ thẻ hình ảnh chủ đề, **E-book Language Readiness**, Freeship toàn quốc và **đổi trả 7 ngày** ạ!"),
        'answer_en': ("I completely understand! **Bloompod is not a random MP3 speaker**, but a complete "
                      "**Language Readiness system built for a 0–3 year old's developing brain** "
                      "(used across the first 3 years — about **1,500 VND a day**).\n\n"
                      "* The offer price of **1,650,000 VND** (save 300,000 VND) includes the structured-cycle audio "
                      "player, Visual Theme Cards, the **Language Readiness e-book**, **free nationwide shipping** and a "
                      "**7-day return policy**."),
    },
    {
        'name': 'Sợ bé không chịu nghe / bỏ xó',
        'sequence': 20,
        'keywords': 'bỏ xó\nkhông chịu nghe\nchán\nbored\nignore\nnot listen\nattention\nsit still',
        'answer_vi': ("Dạ điểm hay nhất của Bloompod là **bé không cần ngồi im chú ý nghe** mới có tác dụng ạ!\n\n"
                      "* Ba/mẹ chỉ cần bật 15–20 phút vào giờ cố định khi bé đang chơi tự do; thính giác bé 0–3 tuổi "
                      "thu nạp thụ động nhịp điệu và âm sắc tiếng Anh.\n"
                      "* Hãng có chính sách **đổi trả trong 7 ngày** nên ba/mẹ hoàn toàn yên tâm trải nghiệm cho con nhé!"),
        'answer_en': ("The best part is that **your child does not need to sit still or focus** for it to work!\n\n"
                      "* Play 15–20 minute sessions at fixed times while your child plays freely; a 0–3 year old "
                      "absorbs rhythm and tone passively.\n"
                      "* There's a **7-day return policy**, so you can try it worry-free."),
    },
    {
        'name': 'Giá & mua hàng',
        'sequence': 30,
        'show_lead_form': True,
        'keywords': 'giá\nbao nhiêu\nmua\nưu đãi\nkit\nprice\nhow much\ncost\nbuy\norder\ndiscount\npromo',
        'answer_vi': ("Dạ bộ **Bloompod Kit** chính hãng hiện có giá ưu đãi **1.650.000đ** (giá gốc 1.950.000đ).\n\n"
                      "* **Trọn bộ gồm:** máy phát âm thanh theo chu kỳ Language Readiness, bộ thẻ hình ảnh theo chủ đề "
                      "và **E-book hướng dẫn cho ba mẹ**.\n"
                      "* **Quyền lợi:** miễn phí giao hàng toàn quốc (kiểm tra hàng khi nhận) và **đổi trả trong 7 ngày**.\n\n"
                      "Ba/mẹ để lại số điện thoại hoặc gọi **0814 433 355** để đặt hàng nhanh nhé!"),
        'answer_en': ("The official **Bloompod Kit** is on offer at **1,650,000 VND** (regular 1,950,000 VND).\n\n"
                      "* **Inside the kit:** the Language Readiness structured-cycle audio system, Visual Theme Cards and a "
                      "**parent's guide e-book**.\n"
                      "* **Benefits:** **free nationwide shipping** (inspect on delivery) and a **7-day return policy**.\n\n"
                      "Leave your number or call/Zalo **0814 433 355** to order."),
    },
    {
        'name': 'Lộ trình sử dụng mỗi ngày',
        'sequence': 40,
        'keywords': 'cả ngày\nmấy lần\nmấy tiếng\nbao lâu\nkhung giờ\nlộ trình\ncách dùng\nall day\nhow many times\nhow long\nschedule\nroutine\nhow to use',
        'answer_vi': ("Dạ ba/mẹ **không cần và không nên mở cả ngày** đâu ạ.\n\n"
                      "* Hiệu quả của Language Readiness đến từ **sự lặp lại có cấu trúc**, không phải âm thanh nền suốt ngày.\n"
                      "* Với bé 0–3 tuổi, chỉ cần **2–3 phiên ngắn mỗi ngày** (15–20 phút/phiên) vào khung giờ cố định "
                      "khi bé tỉnh táo, vui vẻ là tốt nhất ạ!"),
        'answer_en': ("You **don't need to (and shouldn't) play it all day**.\n\n"
                      "* Language Readiness works through **structured repetition**, not background noise.\n"
                      "* For children aged 0–3, play **2–3 short sessions a day (15–20 minutes each)** at fixed, relaxed "
                      "times, 1.5–2.5 m away at a gentle volume."),
    },
    {
        'name': 'Khác gì YouTube / app',
        'sequence': 50,
        'keywords': 'youtube\nkhác gì\nmàn hình\nđiện thoại\nscreen\ntv\napp\ndifference\ndifferent',
        'answer_vi': ("Điểm khác biệt lớn nhất là **Bloompod 100% không màn hình** và dùng **chu kỳ âm thanh có cấu trúc** ạ.\n\n"
                      "* **YouTube / TV / App:** hình ảnh nhấp nháy dễ kích thích quá mức, tạo thói quen phụ thuộc màn hình.\n"
                      "* **Bloompod:** tập trung vào thính giác (Rhythm – Tone – Structure), bé tiếp nhận tự nhiên mà vẫn bảo vệ mắt."),
        'answer_en': ("The biggest difference: **Bloompod is 100% screen-free** and uses **structured audio cycles**.\n\n"
                      "* **YouTube / TV / apps:** flashing visuals overstimulate and build screen dependency.\n"
                      "* **Bloompod:** works on listening alone (Rhythm – Tone – Structure), so children absorb language "
                      "naturally while their eyes stay protected."),
    },
    {
        'name': 'Bảo hành, đổi trả & liên hệ',
        'sequence': 60,
        'keywords': 'bảo hành\nđổi trả\nđịa chỉ\nliên hệ\ncông ty\nđại lý\nsỉ\nwarranty\nreturn\nrefund\naddress\ncontact\ncompany\nshipping\ndelivery\nwholesale',
        'answer_vi': ("Dạ chính sách hỗ trợ khách hàng của **Bloompod.vn** như sau ạ:\n\n"
                      "* **Đổi trả & vận chuyển:** đổi trả linh hoạt trong **7 ngày** và miễn phí giao hàng toàn quốc.\n"
                      "* **Đơn vị vận hành:** Công ty TNHH Giáo dục Toàn cầu Amplify (B2.7.04 Lavida Plus, P. Tân Phong, Quận 7, TP.HCM).\n"
                      "* **Hotline / Zalo:** **0814 433 355** | **Email:** **info@bloompod.vn**"),
        'answer_en': ("Here is **Bloompod.vn**'s support policy:\n\n"
                      "* **Returns & shipping:** **7-day exchange or refund** for any defect, plus **free nationwide shipping**.\n"
                      "* **Operated by:** Amplify Global Education Co., Ltd. (B2.7.04 Lavida Plus, Tan Phong Ward, District 7, HCMC).\n"
                      "* **Hotline / Zalo:** **0814 433 355** | **Email:** **info@bloompod.vn**"),
    },
]

KNOWLEDGE = [
    {
        'name': 'Tổng quan Bloompod & phương pháp Language Readiness cho trẻ 0–3 tuổi',
        'sequence': 1, 'source_type': 'website', 'category': 'Phương pháp',
        'source_url': 'https://bloompod.vn',
        'content': (
            '## Bản chất của Bloompod và khái niệm "Language Readiness"\n'
            'Bloompod là hệ thống phát triển nền tảng ngôn ngữ đầu đời, tập trung vào giai đoạn Language '
            'Readiness (sự sẵn sàng về ngôn ngữ), thiết kế riêng cho trẻ trong 3 năm đầu đời (0–3 tuổi).\n'
            '- Ngôn ngữ bắt đầu từ lắng nghe: trước khi nói, não bộ trẻ cần làm quen với nhịp điệu (rhythm), '
            'âm sắc (tone) và cấu trúc (structure) của ngôn ngữ.\n\n'
            '## Điểm khác biệt so với lớp học, app hay video YouTube\n'
            '- Bloompod không phải lớp học sớm, không phải ứng dụng điện thoại, không phải video giải trí.\n'
            '- Dựa trên 3 trụ cột: chu kỳ lặp lại có cấu trúc; nhịp điệu và âm sắc chuẩn xác; phiên nghe ngắn, '
            'đều đặn, không màn hình.'),
    },
    {
        'name': 'Bộ sản phẩm Bloompod Kit, giá bán & chính sách đổi trả',
        'sequence': 2, 'source_type': 'website', 'category': 'Sản phẩm & giá',
        'source_url': 'https://bloompod.vn',
        'content': (
            '## Bloompod Kit gồm những gì\n'
            '- Hệ thống âm thanh theo chu kỳ (Rhythm – Tone – Structure).\n'
            '- Bộ thẻ hình ảnh theo chủ đề (Visual Theme Cards), không cần màn hình.\n'
            '- E-book "Language Readiness" cho ba mẹ.\n\n'
            '## Giá bán & ưu đãi\n'
            '- Giá niêm yết: 1.950.000 VNĐ / bộ.\n'
            '- Giá ưu đãi: 1.650.000 VNĐ / bộ (tiết kiệm 300.000 VNĐ).\n'
            '- Miễn phí giao hàng toàn quốc, đồng kiểm khi nhận, đổi trả trong 7 ngày.\n\n'
            '## Công ty vận hành & liên hệ\n'
            '- Công ty TNHH Giáo dục Toàn cầu Amplify (MST: 0318833596).\n'
            '- Địa chỉ: B2.7.04 Chung cư Lavida Plus, P. Tân Phong, Quận 7, TP.HCM.\n'
            '- Hotline: 0814 433 355 | Email: info@bloompod.vn'),
    },
    {
        'name': 'Kịch bản xử lý từ chối',
        'sequence': 3, 'source_type': 'manual', 'category': 'Kịch bản bán hàng',
        'content': (
            '## Khi phụ huynh chê đắt\n'
            'Bloompod không phải loa MP3 ngẫu nhiên mà là trọn bộ hệ thống Language Readiness cho trẻ 0–3 tuổi '
            '(dùng suốt 3 năm đầu, khoảng 1.500đ/ngày). Giá ưu đãi 1.650.000đ đã gồm máy phát, bộ thẻ hình ảnh, '
            'e-book, freeship và đổi trả 7 ngày.\n\n'
            '## Khi phụ huynh sợ bé không chịu nghe\n'
            'Bé không cần ngồi im chú ý. Bật phiên 15–20 phút vào giờ cố định khi bé chơi tự do hoặc chuẩn bị ngủ; '
            'thính giác bé thu nạp thụ động. Có đổi trả 7 ngày.'),
    },
    {
        'name': 'Cẩm nang lộ trình nghe 0–3 tuổi',
        'sequence': 4, 'source_type': 'manual', 'category': 'Hướng dẫn sử dụng',
        'content': (
            '## Lộ trình nghe theo độ tuổi\n'
            '- 0–12 tháng: 2–3 phiên ngắn mỗi ngày (15–20 phút/phiên) khi bé vừa ngủ dậy hoặc nằm chơi.\n'
            '- 12–24 tháng: duy trì 2–3 phiên cố định, kết hợp xem bộ thẻ hình ảnh theo chủ đề.\n'
            '- 24–36 tháng: giai đoạn tiền lời nói, bật âm tự nhiên qua các chu kỳ lặp lại.\n\n'
            '## Lưu ý bảo vệ thính giác\n'
            '- Đặt loa cách chỗ bé chơi 1.5–2.5 m, không gian yên tĩnh, tắt TV/điện thoại khi nghe. '
            'Không ép bé đọc theo.'),
    },
]


def load(env, config):
    """Create what is missing; never overwrite what someone has already edited."""
    Qa = env['isd.ai.chatbot.qa'].sudo().with_context(active_test=False)
    Doc = env['isd.ai.chatbot.knowledge'].sudo().with_context(active_test=False)
    qa_count = doc_count = 0
    for vals in QA:
        if not Qa.search_count([('name', '=', vals['name'])]):
            Qa.create(vals)
            qa_count += 1
    for vals in KNOWLEDGE:
        if not Doc.search_count([('name', '=', vals['name'])]):
            Doc.create(vals)
            doc_count += 1
    # A field still holding its install-time default has not been edited by
    # anyone, so the sample may take it; anything else is someone's work
    defaults = config.default_get(list(CONFIG))
    config.sudo().write({k: v for k, v in CONFIG.items()
                         if not config[k] or config[k] == defaults.get(k)})
    return {'qa': qa_count, 'docs': doc_count}
