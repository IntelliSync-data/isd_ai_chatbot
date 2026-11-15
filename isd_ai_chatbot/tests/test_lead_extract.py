# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged

from ..services import lead_extract


@tagged('post_install', '-at_install')
class TestLeadExtract(TransactionCase):

    def test_names(self):
        cases = {
            'Mình là Trần Thị Mai, sđt 0912345678': 'Trần Thị Mai',
            # Many customers type without accents
            'Minh la Moi Toanh, sdt 0901111222': 'Moi Toanh',
            'toi ten la Le Hoa': 'Le Hoa',
            'my name is John Smith': 'John Smith',
            # Words that are also times of day are still names
            'Nguyễn Văn Sáng 0987654321': 'Nguyễn Văn Sáng',
        }
        for message, name in cases.items():
            self.assertEqual(lead_extract.extract_name_and_topic(message)[0], name, message)

    def test_who_someone_is_is_not_a_name(self):
        for message in ('em la sinh vien muon hoi gia', 'em là phụ huynh, sđt 0901234567', 'i am a student', 'ok', 'Cảm ơn'):
            self.assertEqual(lead_extract.extract_name_and_topic(message)[0], '', message)

    def test_name_and_topic(self):
        self.assertEqual(lead_extract.extract_name_and_topic('ten la Nguyen Van An can tu van gia'),
                         ('Nguyen Van An', 'can tu van gia'))

    def test_typed_without_accents(self):
        # The chat must read "gap nhan vien" the way it reads "gặp nhân viên"
        for text in ('cho mình gặp nhân viên tư vấn', 'cho minh gap nhan vien tu van', 'talk to a human'):
            self.assertTrue(lead_extract.is_handoff_request(text), text)
        for text in ('không', 'khong', 'ko', 'no thanks', 'bo qua'):
            self.assertTrue(lead_extract.wants_to_skip(text), text)
        self.assertFalse(lead_extract.wants_to_skip('khong biet gia'))

    def test_questions(self):
        for text in ('học phí bao nhiêu?', 'hoc phi bao nhieu', 'can you help me', 'is it safe for babies'):
            self.assertTrue(lead_extract.looks_like_question(text), text)
        # "can" is also cần typed without accents: this is a topic, not a question
        for text in ('can tu van khoa hoc cho be', 'Phạm Thu Hà', 'minh la An'):
            self.assertFalse(lead_extract.looks_like_question(text), text)

    def test_unaccented_name_keeps_name_like_words(self):
        # "gia" is giá and also the name Gia: a name typed without accents keeps it
        self.assertEqual(lead_extract.extract_name_and_topic('Nguyen Gia Bao 0903 111 222')[0], 'Nguyen Gia Bao')
