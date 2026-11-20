# Bản đồ sửa deck (EDIT MAP)

Deck là tệp PowerPoint gốc: chữ, khung, sơ đồ và biểu đồ (có dữ liệu nhúng) đều sửa trực tiếp được. Có hai cách sửa; đừng trộn lẫn
trên cùng một bản.

**A. Sửa tay trong PowerPoint** (nhanh, cho bản thi). Làm trên bản sao trong `submission/drafts/<thời điểm>/`. Chạy lại script sẽ tạo
thư mục mới, không đè bản đã sửa.

**B. Sửa nguồn rồi dựng lại** (khi số liệu đổi). Các điểm sửa:

| Muốn đổi | Sửa ở đâu | Rồi chạy |
|---|---|---|
| Câu chữ slide chính, lời nói | `submission/deck/story.yaml` (số trong `{ngoặc}` lấy từ dữ liệu) | `build_deck.py`, `notes_doc.py` |
| Câu chữ phụ lục | `submission/deck/appendix.yaml` | `build_deck.py` |
| Thẻ hỏi–đáp | `submission/deck/qa.yaml` | `notes_doc.py` |
| Một con số | chạy lại lần chạy tạo ra nó (notebook), cập nhật đường dẫn run trong `make_data.py` | `make_data.py`, `figures.py`, `build_deck.py` |
| Màu, cỡ chữ, phông | `submission/deck/theme.json` (web dùng cùng giá trị trong `app/static/style.css` và `app.js`) | `build_deck.py`, `figures.py` |
| Bố cục một slide | hàm tương ứng `s1_lot` … `s8_close` trong `build_deck.py` | `build_deck.py` |

Lệnh (từ thư mục gốc):

```bash
python submission/deck/make_data.py && python submission/deck/figures.py && python submission/deck/build_deck.py
```

```bash
python submission/deck/render.py submission/drafts/<thời điểm>/AGQO_BanKet_Slide.pptx
```

## Thao tác thường gặp trong PowerPoint

- **Đổi một con số trên biểu đồ:** chọn biểu đồ → Chart Design → Edit Data → sửa ô → đóng. Màu và định dạng giữ nguyên (đã thử).
- **Đổi tiêu đề:** tiêu đề là placeholder của layout “AGQO Headline”; sửa chữ trực tiếp.
- **Đổi nhãn sơ đồ** (slide 5): mỗi khối là một shape có tên (“S5 Qubit”, “S5 Bit SSI”…) trong Home → Arrange → Selection Pane.
- **Dời hoặc tách slide:** mỗi slide độc lập; slide 3 có 3 lần bấm hiện dần (yêu cầu → ràng buộc → hai danh mục), slide 5 có 4.
  Trạng thái cuối luôn đầy đủ nên bản PDF không thiếu nội dung.
- **Vạch 100% ở slide 1** là một đường thẳng đặt trên biểu đồ với trục cố định 0–120%; nếu đổi trục hoặc cỡ biểu đồ, kéo vạch theo.
- **Đổi theme:** Design → Variants → Colors/Fonts (“AGQO”, “AGQO Arial”); hoặc sửa `theme.json` rồi dựng lại.
- **Bản 3 phút:** slide 1, 3, 4, 8 (xem `docs/submission/LOI_NOI_THUYET_TRINH.md`). Ẩn slide 2, 5, 6, 7 bằng Hide Slide.

## Hình có chữ bên trong

Ảnh màn hình prototype (`docs/prototype_shots/v32/`, chụp bằng `app/capture_v32.py`) giữ nguyên chữ tiếng Việt của giao diện. Hình
in của báo cáo sinh từ `submission/deck/figures.py` với nhãn tiếng Anh; sửa nhãn trong script rồi chạy lại.
