#!/usr/bin/env python3
"""Build a non-canonical Vietnamese terminology inventory for Medical Qigong.

The inventory combines curated, source-grounded terminology with an exhaustive
scan of Han-character/pinyin annotations and uppercase abbreviations in the
complete chunk source.  It intentionally writes under work/ rather than
changing the repository's approved glossary.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path


CURATED: dict[str, list[tuple[str, str, str]]] = {
    "Khái niệm cốt lõi": [
        ("Chinese Medical Qigong (CMQ)", "Khí công Y học Trung Quốc (CMQ)", "Dùng thống nhất; giữ CMQ như viết tắt của nguồn."),
        ("Medical Qigong", "Khí công Y học", "Dùng thống nhất; không dùng ‘Khí công y tế’."),
        ("Qigong", "Khí công", "Viết hoa khi là tên bộ môn/tên bài; viết thường trong nghĩa chung."),
        ("Qigong therapy", "liệu pháp Khí công", "Không đổi thành ‘liệu pháp khí công’ khi chỉ thuật ngữ chuyên ngành."),
        ("Qigongology", "Khí công học", "Giữ sắc thái tên một ngành học."),
        ("Qigong form", "công pháp Khí công", "Dùng cho một phương pháp/bài thực hành cụ thể."),
        ("Qigong state", "trạng thái Khí công", ""),
        ("Qigong practice/exercise", "luyện tập Khí công", ""),
        ("cultivation", "tu luyện", "Dùng trong ngữ cảnh Đạo giáo/Phật giáo; ‘rèn luyện’ khi nói kỹ năng thông thường."),
        ("Qi", "khí (Qi)", "Ở lần đầu trong đoạn có thể ghi ‘khí (Qi)’; sau đó dùng ‘khí’."),
        ("internal Qi", "nội khí", ""),
        ("external Qi", "ngoại khí", ""),
        ("external Qi therapy", "liệu pháp ngoại khí", ""),
        ("Qi emission", "phát ngoại khí", "Không dịch thành ‘phát xạ khí’."),
        ("Qi sensation", "cảm giác khí", ""),
        ("Qi field", "trường khí", ""),
        ("genuine Qi", "chân khí", ""),
        ("original Qi", "nguyên khí", ""),
        ("pectoral Qi", "tông khí", ""),
        ("food Qi", "cốc khí", ""),
        ("Qi point", "khí huyệt", "Giữ pinyin/Hán tự nếu nguồn nêu vị trí chuyên biệt."),
        ("essence", "tinh", ""),
        ("spirit / Shen", "thần (Shen)", ""),
        ("essence-Qi-spirit", "Tinh–Khí–Thần", "Dùng dấu gạch nối dài hoặc en dash nhất quán."),
        ("mind / intention / Yi", "ý (Yi)", "Phân biệt với ‘tâm’ theo ngữ cảnh nguồn."),
        ("mental visualization", "quán tưởng", ""),
        ("keep the mind on", "giữ ý tại", "Cần giữ cấu trúc nguồn ở lần xuất hiện đầu."),
        ("three adjustments", "tam điều", "Dùng thống nhất cho body, breath and mind adjustments."),
        ("adjustment of body", "điều thân", ""),
        ("adjustment of breath", "điều tức", ""),
        ("adjustment of mind", "điều tâm", ""),
        ("integrating the three adjustments into one", "hợp nhất tam điều", "Có thể viết ‘đưa tam điều về một thể’ nếu câu cần tự nhiên."),
    ],
    "Y học Trung Hoa và cơ thể học truyền thống": [
        ("Traditional Chinese Medicine (TCM)", "Y học cổ truyền Trung Quốc (TCM)", "Giữ TCM như viết tắt của nguồn."),
        ("Chinese medicine", "y học Trung Hoa", "Dùng ‘y học cổ truyền Trung Quốc’ nếu nguồn nói rõ TCM."),
        ("zang-fu", "tạng phủ", "Không dùng ‘biểu hiện nội tạng’."),
        ("visceral manifestation", "tạng phủ", "Tương ứng cách dịch chuẩn của zang-fu trong sách."),
        ("meridian theory", "học thuyết kinh lạc", ""),
        ("meridian", "kinh mạch", "‘Kinh lạc’ khi nói hệ thống chung."),
        ("channels and collaterals", "kinh lạc", ""),
        ("acupoint", "huyệt vị", ""),
        ("conception vessel", "mạch Nhâm", ""),
        ("governor vessel", "mạch Đốc", ""),
        ("elixir field / Dantian", "đan điền", "Giữ Dantian ở lần đầu nếu nguồn dùng pinyin."),
        ("upper/middle/lower elixir field", "thượng/trung/hạ đan điền", ""),
        ("Yin-Yang", "Âm–Dương", ""),
        ("Five Elements", "Ngũ hành", ""),
        ("Yin essence", "tinh Âm", ""),
        ("heart Fire", "tâm Hỏa", ""),
        ("kidney Water", "thận Thủy", ""),
        ("ministerial Fire", "tướng Hỏa", ""),
        ("prenatal", "tiên thiên", ""),
        ("postnatal", "hậu thiên", ""),
        ("acquired essence", "hậu thiên chi tinh", "Giữ thuật ngữ gốc ở lần đầu nếu ngữ cảnh đòi hỏi."),
        ("inborn essence", "tiên thiên chi tinh", ""),
        ("health preservation", "dưỡng sinh", ""),
        ("syndrome differentiation", "biện chứng", ""),
        ("treatment based on syndrome differentiation", "luận trị theo biện chứng", ""),
    ],
    "Truyền thống, lý thuyết và tu luyện": [
        ("Daoist Qigong", "Khí công Đạo giáo", ""),
        ("Buddhist Qigong", "Khí công Phật giáo", ""),
        ("Confucian Qigong", "Khí công Nho giáo", "Không dùng ‘Khí công Khổng Tử’."),
        ("Martial Arts Qigong", "Khí công võ thuật", ""),
        ("internal elixir art", "nội đan thuật", ""),
        ("external elixir art", "ngoại đan thuật", ""),
        ("internal elixir Qigong", "Khí công nội đan", ""),
        ("elixir tripod art", "đan lô thuật", "Cần giữ thuật ngữ gốc nếu câu giải thích không rõ."),
        ("Small Heavenly Circulation", "Tiểu chu thiên", ""),
        ("Grand Heavenly Circulation", "Đại chu thiên", ""),
        ("Heavenly Circulation Qigong", "Khí công chu thiên", ""),
        ("stove-ding", "lô–đỉnh", "Giữ ‘Stove-Ding’ ở lần đầu cùng Hán tự khi có."),
        ("Fire Heating Control / Huo Hou", "hỏa hầu", ""),
        ("fierce Fire / Wu Huo", "võ hỏa", ""),
        ("mild Fire / Wen Huo", "văn hỏa", ""),
        ("Kan and Li", "Khảm và Ly", ""),
        ("Eight Trigrams", "Bát quái", ""),
        ("hexagram", "quẻ", ""),
        ("The Book of Changes / Yijing", "Kinh Dịch (Yijing)", ""),
        ("Dao", "Đạo", ""),
        ("Shamatha", "chỉ", "Giữ Shamatha ở lần đầu nếu nguồn có."),
        ("Vipasyana", "quán", "Giữ Vipasyana ở lần đầu nếu nguồn có."),
        ("Shamatha and Vipasyana", "chỉ quán", ""),
        ("Esoteric Buddhism", "Mật tông", ""),
        ("mudra", "thủ ấn", ""),
        ("mantra", "chân ngôn", ""),
        ("lotus position", "thế liên hoa", ""),
    ],
    "Công pháp Khí công": [
        ("Five-Animal Frolics", "Ngũ cầm hí", "Giữ 五禽戏 ở lần đầu nếu nguồn có."),
        ("Six Syllable Formula", "Lục tự quyết", "Giữ 六字诀 ở lần đầu nếu nguồn có."),
        ("Muscle/Tendon Changing Classic", "Dịch cân kinh", "Giữ 易筋经 ở lần đầu nếu nguồn có."),
        ("Eight Pieces of Brocade", "Bát đoạn cẩm", "Giữ 八段锦 ở lần đầu nếu nguồn có."),
        ("Five Elements Palm", "Ngũ hành chưởng", "Giữ 五行掌 ở lần đầu nếu nguồn có."),
        ("Health Preserving Qigong", "Bảo kiện công", "Giữ 保健功 ở lần đầu nếu nguồn có."),
        ("Post Standing Qigong", "Trạm trang công", "Giữ 站桩功 ở lần đầu nếu nguồn có."),
        ("Relaxation Qigong", "Phóng tùng công", "Giữ 放松功 ở lần đầu nếu nguồn có."),
        ("Internal Nourishing Qigong", "Nội dưỡng công", "Giữ 内养功 ở lần đầu nếu nguồn có."),
        ("Roborant Qigong", "Cường tráng công", "Giữ 强壮功 ở lần đầu nếu nguồn có."),
        ("New Qigong Therapy", "Tân Khí công liệu pháp", "Giữ 新气功疗法 ở lần đầu nếu nguồn có."),
        ("dynamic Qigong", "động công", ""),
        ("static Qigong", "tĩnh công", ""),
        ("standing practice", "công pháp đứng", ""),
        ("sitting practice", "công pháp ngồi", ""),
        ("walking practice", "công pháp đi", ""),
        ("lying practice", "công pháp nằm", ""),
        ("Qigong deviation", "lệch lạc khi luyện Khí công", "Không mặc định thay bằng ‘tẩu hỏa nhập ma’ nếu nguồn không nói vậy."),
    ],
    "Nghiên cứu, lâm sàng và bệnh danh": [
        ("physiological effects", "tác động sinh lý", ""),
        ("psychological effects", "tác động tâm lý", ""),
        ("respiratory system", "hệ hô hấp", ""),
        ("cardiovascular system", "hệ tim mạch", ""),
        ("neuroelectrophysiology", "điện sinh lý thần kinh", ""),
        ("EEG", "điện não đồ (EEG)", ""),
        ("EMG", "điện cơ đồ (EMG)", ""),
        ("ECG", "điện tâm đồ (ECG)", ""),
        ("clinical application", "ứng dụng lâm sàng", ""),
        ("indication", "chỉ định", ""),
        ("contraindication", "chống chỉ định", ""),
        ("clinical routine", "quy trình lâm sàng", ""),
        ("hypertension", "tăng huyết áp", ""),
        ("coronary artery disease", "bệnh động mạch vành", ""),
        ("peptic ulcer", "loét dạ dày–tá tràng", ""),
        ("chronic liver disease", "bệnh gan mạn tính", ""),
        ("diabetes mellitus", "đái tháo đường", ""),
        ("obesity", "béo phì", ""),
        ("menopause syndrome", "hội chứng mãn kinh", ""),
        ("chronic fatigue syndrome", "hội chứng mệt mỏi mạn tính", ""),
        ("insomnia", "mất ngủ", ""),
        ("tumor and cancer", "u bướu và ung thư", ""),
        ("lower back pain and leg pain", "đau thắt lưng và đau chân", ""),
        ("cervical spondylosis", "thoái hóa đốt sống cổ", ""),
        ("myopia", "cận thị", ""),
    ],
}

HAN_RE = re.compile(r"[\u3400-\u9fff]")
PAREN_RE = re.compile(r"\(([^()\n]*[\u3400-\u9fff][^()\n]*)\)")
ACRONYM_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,8}\b")
ROMAN_RE = re.compile(r"^(?:I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX|XXVIII)$")


def line_contexts(text: str, value: str, maximum: int = 3) -> list[str]:
    result: list[str] = []
    for line in text.splitlines():
        if value in line:
            compact = " ".join(line.split())
            if compact and compact not in result:
                result.append(compact[:220])
        if len(result) == maximum:
            break
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--approved-output",
        type=Path,
        help="Write the curated entries as an APPROVED domain glossary.",
    )
    args = parser.parse_args()

    source = args.source.resolve()
    text = source.read_text(encoding="utf-8")
    lines: list[str] = [
        "# Danh mục thuật ngữ — *Chinese Medical Qigong*",
        "",
        f"**Nguồn quét:** `{source.name}` — toàn bộ tài liệu nguồn đã làm sạch running header.",
        "",
        "**Trạng thái:** Các mục trong năm bảng đề xuất bên dưới đã được người dùng phê duyệt và được sao chép vào glossary chuyên ngành. Danh sách Hán–pinyin và mã tự quét vẫn chỉ là danh mục rà soát.",
        "",
        "## Quy ước dùng trong bản dịch",
        "",
        "- Ưu tiên thuật ngữ Việt hóa quen dùng trong Khí công và Y học cổ truyền Trung Quốc; lần đầu có thể giữ pinyin/Hán tự kèm theo khi nguồn đã nêu.",
        "- Giữ nguyên tên người, tên sách, tên cơ quan, URL, mã huyệt/kinh, viết tắt và các danh xưng chuyên môn; chỉ chú giải ở lần đầu nếu cần cho nghĩa.",
        "- Không dùng ‘Khí công y tế’ cho *Medical Qigong*. Dùng ‘Khí công Y học’; với *Chinese Medical Qigong*, dùng ‘Khí công Y học Trung Quốc’.",
        "- Không dùng ‘Khí công Khổng Tử’ cho *Confucian Qigong*. Dùng ‘Khí công Nho giáo’.",
        "",
    ]

    for category, rows in CURATED.items():
        lines.extend([f"## {category}", "", "| Nguồn | Đề xuất tiếng Việt | Cách xử lý |", "|---|---|---|"])
        lines.extend(f"| {source_term} | {target_term} | {note} |" for source_term, target_term, note in rows)
        lines.append("")

    han_terms = Counter(match.group(1).strip() for match in PAREN_RE.finditer(text))
    lines.extend([
        "## Thuật ngữ Hán–pinyin trích xuất từ toàn bộ nguồn",
        "",
        "Các mục dưới đây được quét tự động từ mọi chú thích trong ngoặc có chữ Hán. Chúng cần được giữ nguyên cùng Hán tự/pinyin ở lần xuất hiện đầu, sau đó áp dụng cách dịch đã có ở bảng trên hoặc ghi vào phần *Cần kiểm tra thuật ngữ* nếu không đủ ngữ cảnh.",
        "",
        "| Thuật ngữ nguồn | Số lần | Ngữ cảnh nguồn (rút gọn) |",
        "|---|---:|---|",
    ])
    for term, count in sorted(han_terms.items(), key=lambda item: item[0].casefold()):
        contexts = " / ".join(line_contexts(text, term, 1)).replace("|", "\\|")
        lines.append(f"| {term.replace('|', '\\|')} | {count} | {contexts} |")
    lines.append("")

    acronyms = Counter(value for value in ACRONYM_RE.findall(text) if not ROMAN_RE.fullmatch(value))
    lines.extend([
        "## Viết tắt và mã xuất hiện trong toàn bộ nguồn",
        "",
        "Giữ nguyên mã nguồn. Chú giải tiếng Việt ở lần đầu nếu nó là khái niệm chuyên môn; không tự dịch mã huyệt/kinh hay thông số nghiên cứu.",
        "",
        "| Mã/viết tắt | Số lần | Gợi ý xử lý |",
        "|---|---:|---|",
    ])
    expanded = {
        "CMQ": "Khí công Y học Trung Quốc (CMQ)",
        "TCM": "Y học cổ truyền Trung Quốc (TCM)",
        "EEG": "điện não đồ (EEG)",
        "EMG": "điện cơ đồ (EMG)",
        "ECG": "điện tâm đồ (ECG)",
        "CNS": "hệ thần kinh trung ương (CNS)",
        "CAD": "bệnh động mạch vành (CAD)",
        "CFS": "hội chứng mệt mỏi mạn tính (CFS)",
        "MRI": "cộng hưởng từ (MRI)",
        "DNA": "DNA",
        "RNA": "RNA",
        "O2": "O₂",
        "CO2": "CO₂",
    }
    for value, count in sorted(acronyms.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {value} | {count} | {expanded.get(value, 'Giữ nguyên; xác định theo ngữ cảnh nguồn.')} |")
    lines.append("")
    lines.extend([
        "## Cần kiểm tra thuật ngữ",
        "",
        "- Các thuật ngữ Hán–pinyin không có đối ứng trong bảng đề xuất không được tự đặt thành thuật ngữ chuẩn. Giữ nguyên dạng nguồn kèm diễn giải thận trọng ở lần đầu, hoặc đánh dấu để rà soát.",
        "- Các mã kinh lạc/huyệt vị (ví dụ GV, CV, BL, GB, HT, KI, LI, LU, PC, SI, SP, ST) phải giữ đúng mã nguồn; nếu dịch tên huyệt, cần đối chiếu đúng ngữ cảnh của sách.",
        "- Các tiêu đề sách kinh điển có thể giữ tên Latin/pinyin và dịch nghĩa trong ngoặc ở lần đầu, để tránh khẳng định sai một tên Hán–Việt khi nguồn không đủ rõ.",
        "",
    ])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    if args.approved_output:
        glossary_lines = [
            "# Qigong Glossary",
            "",
            "**Language pair:** English → Vietnamese  ",
            "**Domain:** Qigong, Medical Qigong, and Traditional Chinese Medicine  ",
            "**Status:** APPROVED by the user on 2026-08-26.",
            "",
            "Use these renderings exactly for all Qigong-related documents. Terms explicitly referring to *Chinese Medical Qigong* apply only when that source term appears. The source inventory in `work/medical_qigong/TERMINOLOGY_CANDIDATES.md` contains additional Hán–pinyin forms and codes that remain context-dependent; do not treat those automatically extracted entries as approved translations.",
            "",
        ]
        for category, rows in CURATED.items():
            glossary_lines.extend([f"## {category}", "", "| Source term | Approved rendering | Status | Scope / notes |", "|---|---|---|---|"])
            glossary_lines.extend(
                f"| {source_term} | {target_term} | APPROVED | {note} |"
                for source_term, target_term, note in rows
            )
            glossary_lines.append("")
        args.approved_output.parent.mkdir(parents=True, exist_ok=True)
        args.approved_output.write_text("\n".join(glossary_lines), encoding="utf-8")
    print(f"Wrote {args.output} with {sum(len(rows) for rows in CURATED.values())} curated entries, {len(han_terms)} Han/pinyin annotations, and {len(acronyms)} abbreviations.")
    if args.approved_output:
        print(f"Wrote APPROVED domain glossary: {args.approved_output}")


if __name__ == "__main__":
    main()
