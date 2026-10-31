# AGQO Repair — hướng dẫn chạy và đọc kết quả

Nhánh mới giải quyết **bảo trì danh mục bám chỉ số khi mandate thay đổi**. Mã legacy và kết quả cũ vẫn nằm nguyên tại `agqo/` và `results/final/`; các số liệu cũ không phải bằng chứng cho nhánh repair.

## Khởi động

Từ thư mục dự án, dùng Python trong `.venv`:

```sh
.venv/bin/python -m agqo.repair fetch-or
.venv/bin/python -m agqo.repair demo --export-circuit
.venv/bin/python -m agqo.repair serve
```

Mở [giao diện cục bộ](http://127.0.0.1:8765). Kiểm tra cách hệ thống hiểu mandate, sau đó tìm phương án. JSON quyết định tải được ngay trên giao diện. API không đặt lệnh và chỉ bind loopback.

Các lệnh không bật LLM mặc định. Muốn dùng Qwen thật:

```sh
.venv/bin/modal deploy modal_qwen3_agqo.py
.venv/bin/python -m agqo.repair demo --llm modal --export-circuit
.venv/bin/python -m agqo.repair serve --llm modal
```

`repair_json` là endpoint riêng trong app `agqo-qwen3-guide`; endpoint policy cũ vẫn được giữ. Có thể đổi app bằng `AGQO_QWEN3_MODAL_APP`. Revision mô hình theo cấu hình đã pin trong dự án. Audit ghi request hash, prompt version, raw response, số token, retry và latency. Hóa đơn USD không được API cung cấp nên để `null`.

## Ngữ pháp baseline

Ví dụ có thể chạy ngay:

```text
Giữ 4 mã; Loại mã S00; Tỷ trọng ngành Banks không quá 25%; Turnover không quá 120%
Hold 4 assets; Must hold S07; Exclude S00; Cost weight 0.01
```

Quy tắc hỗ trợ cardinality đúng bằng K, giữ/loại mã, trần tỷ trọng ngành, turnover hai chiều và hệ số chi phí. Phân cách yêu cầu bằng dấu `;`. Số viết bằng chữ, ngoại lệ phức tạp và yêu cầu chưa được hỗ trợ cần làm rõ; hệ thống không suy đoán. Khi chọn Qwen, vẫn phải vượt qua kiểm tra kiểu, đơn vị, mã/ngành và evidence span.

Turnover = `sum(abs(w_target - w_previous_drifted))`, miền `[0,2]`; vì vậy 120% nghĩa là 1,2, không phải giới hạn 100% theo một chiều. Chi phí = `sum(rate_i * abs(delta_i))`, rate là phí mỗi chiều. Mô hình chưa giải bài toán khớp lệnh, spread quan sát, tác động thị trường, thuế hay số lô thực tế.

## Chạy benchmark

```sh
.venv/bin/python -m agqo.repair benchmark --output results/repair --evaluations 24 --shots 128 --seeds 11,23
.venv/bin/python -m agqo.repair benchmark --source or-library --output results/repair/or_library --evaluations 24 --shots 128 --seeds 11,23
.venv/bin/python -m agqo.repair benchmark --llm modal --output results/repair/live --evaluations 24 --shots 128 --seeds 11,23
```

Mỗi thư mục có `protocol.json` viết trước khi chấm test, `benchmark.json`, `mandates_gold.json`, `summary.json/csv`, bảy hình có catalog và báo cáo Markdown/HTML. Protocol ghi hash mã nguồn, hash từng bài toán, cửa sổ, seeds, shots, thư viện mạch và ngân sách. Cấu hình cố định được chọn **chỉ trên development**. Hệ số chi phí và ngưỡng tái cân bằng là giả định khai báo trước, không phải mức đã được quỹ xác nhận.

Các họ test gồm thị trường thay đổi, cùng thị trường nhưng mandate thay đổi, tổ hợp yêu cầu chưa thấy và yêu cầu không có nghiệm. Corpus ngôn ngữ có nhãn biên soạn độc lập; kích thước nhỏ, chỉ dùng chẩn đoán. Không coi việc vượt corpus này là bằng chứng hiểu mandate bất kỳ.

Chạy lại với replay: chuyển các dòng audit thành đối tượng `{request_hash: envelope}` rồi dùng `--llm replay --replay-file PATH`. Replay được gắn nhãn, không tính là suy luận trực tiếp mới.

## Dữ liệu thật do người dùng xác minh

CSV dạng wide gồm `date,benchmark,TICKER1,...`, giá trị là lợi suất mỗi kỳ, không phải giá. Manifest cần `source`, `sectors` (mapping theo mã) và ba xác nhận boolean `price_adjustment_verified`, `point_in_time_universe_verified`, `benchmark_verified`. Đó là xác nhận do người cung cấp chịu trách nhiệm; mã không tự chứng nhận nguồn thị trường.

```sh
.venv/bin/python -m agqo.repair benchmark --source market --market-csv PATH --market-manifest PATH --output results/repair/market
```

Nguồn OR-Library được tải từ [tác giả](https://people.brunel.ac.uk/~mastjjb/jeb/orlib/indtrackinfo.html), parser kiểm tra đủ `(N+1)*(T+1)` giá dương. Manifest lưu URL và SHA-256. Raw file không đưa vào Git vì chưa xác nhận quyền tái phân phối. Nguồn này không có nhãn ngành hoặc ngày trong tệp; không gán ngành giả và không tự năm hóa. Benchmark QAOA dùng tám mã đầu được khai báo rõ. `screening_audit` đo mất mát so với MILP toàn bộ 31 mã trên cùng điều kiện.

## Encoding và giới hạn tài nguyên

Hàm tracking MSE + chi phí được đổi thành QUBO chính xác, có kiểm tra mọi bit trên bài nhỏ. Đối với toàn bộ hard constraints, prototype tạo bảng diagonal có `2^N` phần tử: mục tiêu chuẩn hóa trong `[0,1]`, cộng barrier `2` nếu vi phạm. Đây là oracle finite-table **không phải QUBO không biến phụ**. Việc dựng bảng có chi phí cổ điển hàm mũ, giới hạn N<=12 và được tính thời gian.

Grammar gồm X/single hoặc XY/ring/complete, p=1/2, khởi tạo previous/random. Khởi tạo previous chọn K mã tỷ trọng cao nhất; trạng thái đầu có thể chưa đáp ứng mandate mới. XY chỉ bảo toàn K. Ở p=1 với khởi tạo basis, cost layer đầu chỉ gây pha toàn cục; baseline độ sâu 2 và khởi tạo random giúp nhìn thấy giới hạn này. Chưa có tuyên bố warm-start relaxation chuyên biệt hoặc QPU.

`--export-circuit` sinh QASM 3 từ mạch Qiskit thực và ghi độ sâu/CX sau transpile sang bộ cổng chung. Metadata này không đại diện backend phần cứng cụ thể. Tests so trạng thái Qiskit với simulator, bao gồm phase oracle và thứ tự qubit.

## Cách đọc kết luận

- Đọc feasibility và thất bại cùng với trung bình chất lượng: trung bình đẹp trên một vài nghiệm thành công không đủ.
- `infeasible` chỉ được báo khi exact/HiGHS chứng minh; không tìm được nghiệm trong ngân sách là `unknown`.
- Qwen disabled/error/invalid không được thay bằng quy tắc rồi gắn nhãn LLM.
- Theo dõi mục tiêu, tracking, turnover và phí riêng. Energy QAOA thấp không tự chứng minh giá trị nghiệp vụ.
- Test lịch sử có chia thời gian không phải một giai đoạn tương lai hoàn toàn mới. Seed và các mandate dùng chung một cửa sổ không phải các mẫu tài chính độc lập.

Chạy kiểm tra:

```sh
.venv/bin/python -m pytest
```
