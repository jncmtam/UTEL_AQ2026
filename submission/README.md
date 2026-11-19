# Hồ sơ dự thi AGQO V3

Các script ở đây đọc bằng chứng từ `results/final/`, hình minh họa trong `docs/` và mẫu báo cáo trong `template/`. Chạy từ gốc repository sau khi cài `.[submission]` hoặc `requirements.txt`.

```bash
python submission/build_report.py submission/template/mau_bao_cao_BTC.docx
python submission/build_guide.py
python submission/build_slides.py results/final/llm/prototype_live_example.json
```

Các tệp Word và PowerPoint được ghi vào `submission/out/`. Điền thông tin đội và kiểm tra bản hiển thị trước khi xuất PDF. Tên tệp có `Madoi` là chỗ điền mã đội. Các tệp đã xuất nằm ngoài Git.

Tạo ZIP mã nguồn từ commit hoặc tag của V3. Công cụ kiểm tra các đường dẫn cục bộ và từ chối ghi đè gói đã có:

```bash
python -m submission.build_source --ref HEAD
```

ZIP giữ mã nguồn, mẫu báo cáo và các bằng chứng đã commit. Tệp giá gốc và các tệp cá nhân hoặc sinh ra trong lúc chạy nằm ngoài Git. Xem [quy trình dùng dữ liệu](../data/vn30/README.md) trước khi chuẩn bị gói phân phối.
