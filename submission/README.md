# Hồ sơ nộp

Bốn tệp nộp theo yêu cầu của Ban tổ chức, đặt tên theo mã đội `AQ2026-169`. Các tệp đã xuất và thông tin cá nhân của đội
nằm ngoài Git (`submission/final/`, `submission/team.local.json`); thư mục này chỉ giữ công cụ dựng chúng.

| Tệp nộp | Công cụ | Ghi chú |
|---|---|---|
| `AQ2026-R2-AQ2026-169-Bao_cao_giai_phap.pdf` | `report/figures.py` → `report/build_report.py` | 12 trang theo mẫu `template/mau_bao_cao_BTC.docx` |
| `AQ2026-R2-AQ2026-169-Slide.pptx` | `deck/make_data.py` → `deck/build_deck.py` | 8 slide chính + 13 phụ lục, ghi chú người nói |
| `AQ2026-R2-AQ2026-169-Ma_nguon.zip` | `source/build_source.py` | `git archive` của một commit, không có tệp giá |
| `AQ2026-R2-AQ2026-169-Huong_dan.pdf` | `guide/build_guide.py` | Từ `docs/guides/HUONG_DAN_GIAM_KHAO.md` và `TAI_LAP.md` |

Prototype: https://data1--agqo-prototype.us-east.modal.run

## Cấu trúc

```text
submission/
├── report/
│   ├── figures.py        Hình báo cáo (tiếng Anh, vẽ đúng cỡ in) → report/figures/
│   ├── build_report.py   Áp các chỉnh sửa lên bản Word đội đã biên tập
│   └── docx2pdf.py       Xuất PDF bằng Microsoft Word, in số trang
├── deck/
│   ├── story.yaml, appendix.yaml, qa.yaml   Nội dung slide, phụ lục, câu hỏi phản biện
│   ├── make_data.py      Bảng số liệu cho biểu đồ (chỉ đọc kết quả đã lưu)
│   ├── build_deck.py     Dựng PPTX: biểu đồ gốc, chữ sửa được, hiệu ứng, ghi chú
│   ├── render.py         PDF dự phòng và ảnh xem nhanh
│   └── EDIT_MAP.md       Sửa chỗ nào trong slide mà không vỡ bố cục
├── guide/build_guide.py  Hướng dẫn cài đặt và sử dụng
├── source/build_source.py  ZIP mã nguồn
└── template/             Mẫu báo cáo của Ban tổ chức
```

## Lệnh

Chạy từ gốc repository sau khi cài `pip install -e '.[submission]'`. Mỗi lệnh ghi vào một thư mục mới trong
`submission/drafts/`, không ghi đè bản đã sửa tay.

```bash
python submission/report/figures.py
```

```bash
python submission/report/build_report.py <bản-word-của-đội>.docx
```

```bash
python submission/report/docx2pdf.py submission/drafts/report-<giờ>/AQ2026-R2-AQ2026-169-Bao_cao_giai_phap.docx
```

```bash
python submission/deck/make_data.py && python submission/deck/build_deck.py
```

```bash
python submission/deck/render.py submission/drafts/<giờ>/AQ2026-R2-AQ2026-169-Slide.pptx
```

```bash
python submission/guide/build_guide.py
```

```bash
python submission/source/build_source.py --out submission/out/AQ2026-R2-AQ2026-169-Ma_nguon.zip
```

## Lưu ý

- **Báo cáo** đi từ bản Word đội đã biên tập (có số CCCD, email, điện thoại nên không đưa lên Git). `build_report.py`
  chỉ thay hình, thuật ngữ, bảng tham số, các ô “Vì sao / Con số nói gì” và dữ kiện của hồ sơ (mã đội, thành viên, đường
  dẫn, tên tệp); thông tin thành viên đọc từ `submission/team.local.json` lúc chạy.
- **ZIP mã nguồn** không có tệp giá DNSE (không có quyền phân phối lại). Người nhận đặt tệp giá vào
  `data/vn30/ohlcv_daily.csv` hoặc chạy `python -m agqo download`, rồi kiểm tra mã băm với `data/vn30/manifest.json`.
- Trước khi nộp, đọc [docs/submission/BAN_GIAO.md](../docs/submission/BAN_GIAO.md): danh sách kiểm tra và các điểm đội cần
  xác nhận.
