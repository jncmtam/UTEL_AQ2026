"""Build the installation / usage / testing guide -> AQ2026-R2-Madoi-Huong_dan.docx (PDF via Word).

    python submission/build_guide.py
"""

from __future__ import annotations

import json
from pathlib import Path

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
SHOT = ROOT / "docs" / "prototype_shots"
RUN = ROOT / "results" / "final"
OUT = ROOT / "submission" / "out" / "AQ2026-R2-Madoi-Huong_dan.docx"
URL = "https://data1--agqo-demo.us-east.modal.run"
TEAL, INK, MUTED = RGBColor(0x0F, 0x4C, 0x5C), RGBColor(0x1F, 0x29, 0x37), RGBColor(0x4B, 0x55, 0x63)
FONT = "Times New Roman"

st = json.loads((RUN / "quantum_stats.json").read_text())
man = json.loads((RUN / "run_manifest.json").read_text())


def shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:color"), "auto")
    sh.set(qn("w:fill"), hex_fill)
    tcPr.append(sh)


class Guide:
    def __init__(self):
        self.d = docx.Document()
        sec = self.d.sections[0]
        sec.page_width, sec.page_height = Cm(21), Cm(29.7)
        sec.left_margin = sec.right_margin = Cm(2.0)
        sec.top_margin, sec.bottom_margin = Cm(1.8), Cm(1.8)
        st_ = self.d.styles["Normal"]
        st_.font.name, st_.font.size = FONT, Pt(11)
        st_.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        st_.paragraph_format.space_after = Pt(4)
        for lvl, size in ((1, 15), (2, 12.5)):
            h = self.d.styles[f"Heading {lvl}"]
            h.font.name, h.font.size, h.font.bold, h.font.color.rgb = FONT, Pt(size), True, TEAL
            h.element.rPr.rFonts.set(qn("w:ascii"), FONT)
            h.element.rPr.rFonts.set(qn("w:hAnsi"), FONT)
            h.paragraph_format.space_before = Pt(12 if lvl == 1 else 8)
            h.paragraph_format.space_after = Pt(4)
            h.paragraph_format.keep_with_next = True
        footer = sec.footer.paragraphs[0]
        footer.text = "AGQO · AI–Quantum Challenge 2026 · Hướng dẫn cài đặt, sử dụng và chạy thử"
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in footer.runs:
            r.font.size, r.font.color.rgb = Pt(8.5), MUTED
        self.fig = 0

    def h(self, text, lvl=1):
        return self.d.add_heading(text, level=lvl)

    def p(self, text, size=11, italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, color=INK, bullet=False):
        par = self.d.add_paragraph(style="List Bullet" if bullet else None)
        par.alignment = align
        for k, seg in enumerate(text.split("**")):
            if seg:
                r = par.add_run(seg)
                r.bold, r.italic = k % 2 == 1, italic
                r.font.size, r.font.color.rgb, r.font.name = Pt(size), color, FONT
        return par

    def code(self, text):
        t = self.d.add_table(rows=1, cols=1)
        c = t.rows[0].cells[0]
        shade(c, "F1F5F9")
        c.paragraphs[0].text = ""
        for i, line in enumerate(text.strip("\n").split("\n")):
            par = c.paragraphs[0] if i == 0 else c.add_paragraph()
            par.paragraph_format.space_after = Pt(0)
            r = par.add_run(line)
            r.font.name, r.font.size, r.font.color.rgb = "Courier New", Pt(9.5), RGBColor(0x0F, 0x17, 0x2A)
        self.d.add_paragraph().paragraph_format.space_after = Pt(2)

    def table(self, header, rows, widths):
        t = self.d.add_table(rows=1, cols=len(header))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.style = "Table Grid"
        for c, txt, w in zip(t.rows[0].cells, header, widths):
            shade(c, "0F4C5C")
            c.width = Cm(w)
            r = c.paragraphs[0].add_run(txt)
            r.bold, r.font.size, r.font.color.rgb = True, Pt(10), RGBColor(0xFF, 0xFF, 0xFF)
        for k, row in enumerate(rows):
            cells = t.add_row().cells
            for c, txt, w in zip(cells, row, widths):
                c.width = Cm(w)
                if k % 2:
                    shade(c, "F3F6F8")
                par = c.paragraphs[0]
                par.paragraph_format.space_after = Pt(0)
                for j, seg in enumerate(str(txt).split("**")):
                    if seg:
                        r = par.add_run(seg)
                        r.bold, r.font.size = j % 2 == 1, Pt(9.5)
        self.d.add_paragraph().paragraph_format.space_after = Pt(2)
        return t

    def image(self, path, width_cm, caption):
        par = self.d.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.keep_with_next = True
        par.add_run().add_picture(str(path), width=Cm(width_cm))
        self.fig += 1
        self.p(f"Hình {self.fig}. {caption}", size=9.5, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, color=MUTED)

    def pagebreak(self):
        self.d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def build() -> Path:
    g = Guide()
    a = st["agqo vs warm_start_only"]
    sw = man["sweep_ci"]["20000000"]

    # ------------------------------------------------------------ cover
    for _ in range(4):
        g.d.add_paragraph()
    g.p("AI–QUANTUM CHALLENGE 2026 · VÒNG 2", 13, align=WD_ALIGN_PARAGRAPH.CENTER, color=TEAL)
    g.p("**TÀI LIỆU HƯỚNG DẪN CÀI ĐẶT, SỬ DỤNG VÀ CHẠY THỬ**", 20, align=WD_ALIGN_PARAGRAPH.CENTER, color=TEAL)
    g.p("AGQO – Danh mục bám VN30 bằng lô chẵn cho nhà đầu tư nhỏ, do AI dẫn dắt và tối ưu bằng mạch lượng tử QAOA", 14,
        align=WD_ALIGN_PARAGRAPH.CENTER)
    g.d.add_paragraph()
    g.image(SHOT / "00_hero.png", 15.5, "Trang chính của prototype.")
    g.p(f"**Link prototype:** {URL}", 12.5, align=WD_ALIGN_PARAGRAPH.CENTER, color=TEAL)
    g.p("Không cần tài khoản · không cần cài đặt · chạy trên trình duyệt Chrome, Edge, Firefox, Safari", 11,
        align=WD_ALIGN_PARAGRAPH.CENTER, color=MUTED)
    g.d.add_paragraph()
    g.p("Mã đội: [Mã đội] · Tên đội: [Tên đội] · Phiên bản v3.1 (16/11/2026)", 11, align=WD_ALIGN_PARAGRAPH.CENTER, color=MUTED)
    g.pagebreak()

    # ------------------------------------------------------------ 1
    g.h("1. Tổng quan và hồ sơ nộp")
    g.p("AGQO giúp nhà đầu tư cá nhân vốn nhỏ nắm giữ danh mục bám chỉ số VN30 theo quy tắc riêng, chỉ bằng lệnh lô chẵn 100 cổ "
        "phiếu. Quy trình: LLM Qwen3.8-27B dịch yêu cầu tiếng Việt thành ràng buộc → thống kê đọc thị trường → bài toán trở thành "
        "Hamiltonian 16 qubit → mô hình k-NN chọn cấu hình mạch → mạch QAOA lấy 512 mẫu → liệt kê cổ điển 65.536 tổ hợp để kiểm "
        "chứng → danh sách lệnh và lời giải thích tiếng Việt.")
    g.table(["Thành phần", "Tệp / đường dẫn", "Nội dung"], [
        ["Báo cáo giải pháp", "AQ2026-R2-Madoi-Bao_cao_giai_phap.pdf", "12 trang theo mẫu BTC"],
        ["Slide trình bày", "AQ2026-R2-Madoi-Slide.pptx", "20 trang, chuyển cảnh và hoạt ảnh, lời nói trong ghi chú"],
        ["Mã nguồn", "AQ2026-R2-Madoi-Ma_nguon.zip", "mã nguồn có chú thích, dữ liệu, kết quả, kiểm thử"],
        ["Hướng dẫn", "AQ2026-R2-Madoi-Huong_dan.pdf", "tài liệu này"],
        ["Prototype", URL, "web app công khai, không cần tài khoản"]], [3.6, 6.6, 6.8])

    # ------------------------------------------------------------ 2
    g.h("2. Chạy thử nhanh trên prototype (không cần cài đặt)")
    g.h("2.1. Truy cập và tài khoản thử nghiệm", 2)
    g.p(f"Mở **{URL}** bằng trình duyệt. Prototype **không yêu cầu đăng nhập**, nên không cần tài khoản thử nghiệm. Lần truy cập đầu "
        "sau một thời gian nghỉ, máy chủ khởi động trong khoảng 8–10 giây (máy chủ tự tắt khi không dùng để tiết kiệm chi phí).")
    g.h("2.2. Chạy một quyết định", 2)
    for t in ["Kéo xuống mục **02 · Thử ngay**. Nhập **số vốn** (triệu đồng, ví dụ 20) và **yêu cầu tiếng Việt** (có thể bỏ trống), "
              "hoặc bấm một câu ví dụ.",
              "Bấm **▶ Chạy AGQO**. Bảy bước hiện lần lượt, mỗi bước một bảng có biểu đồ và chú thích (Hình 2–4).",
              "Bấm **✦ Giải thích bằng AI** để Qwen3.8 viết lời giải thích tiếng Việt; mọi con số được tô xanh nếu có trong bằng chứng.",
              "Bấm **⤓ Tải mạch OpenQASM** để tải mạch lượng tử của quyết định (chạy được trên Qiskit / IBM Quantum)."]:
        g.p(t, bullet=True)
    g.image(SHOT / "form.png", 16.0, "Ô nhập số vốn, yêu cầu tiếng Việt, các câu ví dụ và nút Chạy AGQO.")
    g.h("2.3. Ý nghĩa bảy bước", 2)
    g.table(["Bước", "Hiển thị", "Cách kiểm tra"], [
        ["① AI đọc yêu cầu", "ràng buộc (chip) + JSON của LLM; nguồn: câu trả lời thật của Qwen3.8 hoặc quy tắc từ khoá",
         "đối chiếu chip với câu đã nhập"],
        ["② AI đọc thị trường", "số cược độc lập, nhân tố thị trường, tương quan, các cụm mã", "VN30 ≈ 13–14 cược độc lập"],
        ["③ Hamiltonian", "công thức E(x), ma trận tương tác J 16×16, giá lô và xác suất nới lỏng", "mỗi qubit = một mã"],
        ["④ AI thiết kế mạch", "5 đặc trưng hôm nay so với 10 láng giềng 2023; lịch p, ε, khối lượng J, Δγ, Δβ", "k = 10; 1.080 lịch"],
        ["⑤ Mạch QAOA", "sơ đồ mạch 16 qubit với từng cặp ZZ thật; góc γ, β theo lớp; số cổng", "1.440 cổng 2 qubit khi p = 6"],
        ["⑥ Lấy mẫu + kiểm chứng", "phân bố xác suất 4 cách lấy mẫu; 12 trạng thái xác suất cao nhất; kết luận",
         "dòng xanh: lựa chọn tốt nhất = tối ưu chính xác?"],
        ["⑦ Danh mục và lệnh", "sai số bám dự kiến, tỷ trọng từng mã, bảng lệnh, phí, tiền mặt còn lại, kiểm tra quy tắc",
         "mọi dòng kiểm tra có dấu ✔"]], [3.4, 8.4, 5.2])
    g.image(SHOT / "p6_sampling.png", 15.5, "Bước ⑥: xác suất dồn về nghiệm tốt; kết luận đối chiếu với tối ưu chính xác.")
    g.image(SHOT / "p7_portfolio.png", 15.5, "Bước ⑦: sai số bám của các cách chọn lô, tỷ trọng, lệnh mua và kiểm tra trước khi đặt lệnh.")
    g.h("2.4. Gọi LLM trực tiếp và các kịch bản thử", 2)
    g.p("Các **câu ví dụ** dùng câu trả lời đã ghi lại từ lần chạy thật của Qwen3.8 (hiện ngay). Với **câu mới**, nếu ô “Gọi Qwen3.8 "
        "trực tiếp” được chọn, prototype hiển thị ngay kết quả của quy tắc từ khoá và gửi câu lên GPU H100; GPU đang nghỉ cần khoảng "
        "**6 phút** để khởi động (lần đo: 440 giây), sau đó kết quả LLM tự thay thế và AGQO tự chạy lại nếu ràng buộc khác. Giới hạn 40 "
        "lời gọi LLM mỗi giờ để kiểm soát chi phí.")
    g.table(["Kịch bản", "Nhập", "Kết quả mong đợi"], [
        ["Không yêu cầu", "vốn 20, ô yêu cầu trống", "danh mục lô chẵn; bước ⑥ báo lựa chọn tốt nhất so với tối ưu chính xác"],
        ["Loại mã", "“Không mua VIC, VHM, VRE vì tôi đã có nhiều cổ phiếu nhóm này”", "không có VIC, VHM, VRE trong lệnh"],
        ["Giới hạn ngành", "“Ngân hàng tối đa 30%”", "dòng kiểm tra Banking ≤ 30% có ✔"],
        ["Câu mơ hồ", "“Tôi muốn ít rủi ro hơn”", "LLM hỏi lại cách giảm rủi ro"],
        ["Câu mới (LLM trực tiếp)", "“Tôi làm ở ngân hàng nên không muốn giữ thêm cổ phiếu ngân hàng, và giữ lại 10% tiền mặt”",
         "từ khoá: chỉ tiền mặt 10%; Qwen3.8: loại ngành Ngân hàng + tiền mặt ≥ 10%"],
        ["Vốn lớn", "vốn 100", "lô nhỏ so với vốn: nhiều mã hơn, ít tiền nhàn rỗi, sai số bám thấp hơn tài khoản 20 triệu"]], [3.0, 7.2, 6.8])
    g.p(f"**Link tự chạy:** thêm tham số vào địa chỉ, ví dụ {URL}/?run=1&live=0&capital=20&q=Ngân hàng tối đa 30% "
        "(trình duyệt tự mã hoá dấu cách và tiếng Việt).", size=10.5)

    # ------------------------------------------------------------ 3
    g.h("3. Cài đặt và chạy trên máy cá nhân")
    g.h("3.1. Yêu cầu môi trường", 2)
    g.table(["Hạng mục", "Yêu cầu"], [
        ["Hệ điều hành", "macOS 13+, Ubuntu 22.04+ hoặc Windows 10/11 (PowerShell)"],
        ["Python", "3.12 (đã thử 3.12.12); 3.10–3.11 cũng chạy được phần lõi"],
        ["Phần cứng", "CPU 4 nhân, RAM 8 GB, 500 MB đĩa trống; **không cần GPU**"],
        ["Thư viện chính", "numpy, scipy, pandas, matplotlib, qiskit 2.5, fastapi, uvicorn (requirements.txt)"],
        ["Tuỳ chọn", "tài khoản Modal để gọi LLM trực tiếp; IBM Quantum để chạy phần cứng thật"]], [4.0, 13.0])
    g.h("3.2. Cài đặt (khoảng 5–10 phút)", 2)
    g.code("""unzip AQ2026-R2-Madoi-Ma_nguon.zip -d agqo && cd agqo
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt""")
    g.h("3.3. Chạy prototype cục bộ", 2)
    g.code("""AGQO_LIVE_LLM=0 uvicorn app.server:api --port 8000
# Windows: set AGQO_LIVE_LLM=0  rồi  uvicorn app.server:api --port 8000
# mở trình duyệt: http://localhost:8000""")
    g.p("Không có tài khoản Modal: đặt AGQO_LIVE_LLM=0; prototype dùng câu trả lời đã ghi lại của Qwen3.8 cho các câu ví dụ và quy "
        "tắc từ khoá cho câu mới. Mọi phần còn lại (QAOA, kiểm chứng, lệnh) chạy đầy đủ trên CPU.")
    g.h("3.4. Kiểm thử tự động", 2)
    g.code("pytest -q            # mong đợi: 25 passed (khoảng 3 giây)")

    # ------------------------------------------------------------ 4
    g.h("4. Tái lập toàn bộ kết quả")
    g.table(["Lệnh", "Việc làm", "Thời gian"], [
        ["python -m agqo download", "tải lại dữ liệu DNSE (dữ liệu đã có sẵn trong data/vn30)", "~2 phút"],
        ["python -m agqo mandates --llm replay", "đánh giá 35 câu yêu cầu, phát lại LLM từ nhật ký (không GPU)", "giây"],
        ["python -m agqo run", "huấn luyện 2023, thiết kế mạch, kiểm định 12 quý, thống kê", "~20 phút CPU"],
        ["python -m agqo explain --llm replay", "12 lời giải thích, kiểm tra số và ý nghĩa", "giây"],
        ["python -m agqo extras", "phần cứng (nhiễu IBM), mở rộng 8–20 qubit, độ bền", "10–20 phút"],
        ["python -m agqo report", "hình và docs/RESULTS.md", "~1 phút"],
        ["python -m agqo.figures_vi", "hình tiếng Việt cho slide và báo cáo", "~30 giây"]], [5.6, 8.6, 2.8])
    g.p("Kết quả được ghi vào results/final; thư mục đã có sẵn kết quả của lần chạy chính thức để đối chiếu. Hạt giống ngẫu nhiên cố định "
        "nên các con số tái lập giống hệt.")

    # ------------------------------------------------------------ 5
    g.h("5. Kiểm tra kết quả")
    g.table(["Chỉ số", "Giá trị", "Tệp kiểm tra"], [
        ["Sai số bám, tài khoản 20 triệu (làm tròn → AGQO)", f"{sw['te_b']:.1f}% → {sw['te_a']:.1f}%".replace(".", ","), "results/final/run_manifest.json (sweep_ci)"],
        ["Lượt đo trúng nghiệm gần tối ưu: AGQO / khởi động ấm", f"{100 * a['mean_a']:.1f}% / {100 * a['mean_b']:.1f}% ({a['ratio']:.1f}×)".replace(".", ","),
         "results/final/quantum_stats.json"],
        ["Thắng / Wilcoxon p", f"{a['wins']}/12 · p = 0,0005", "results/final/quantum_stats.json"],
        ["LLM dịch yêu cầu (Qwen3.8 / từ khoá)", "35/35 · 68,6%", "results/final/llm/mandate_eval.json"],
        ["Lời giải thích: đúng số / đúng ý nghĩa", "12/12 · 11/12", "results/final/llm/explanations.json"],
        ["Vi phạm quy tắc cá nhân", "0", "results/final/mandates.csv"],
        ["Mạch theo nhiễu IBM Heron vs khởi động ấm", "1,6× · 11/12 quý", "results/final/extras/hardware_aware.csv"],
        ["Nhật ký mọi lời gọi LLM", "prompt, đầu ra, token, thời gian", "results/final/llm/llm_log.jsonl"]], [6.6, 4.4, 6.0])
    g.p("Trên prototype, mỗi quyết định tự kiểm chứng: dòng kết luận ở bước ⑥ cho biết lựa chọn tốt nhất trong 512 lượt đo có trùng "
        "tối ưu chính xác (liệt kê đủ 2¹⁶ tổ hợp) hay không, và bước ⑦ liệt kê từng quy tắc với giá trị thực tế.")

    # ------------------------------------------------------------ 6
    g.h("6. Tuỳ chọn: LLM trực tiếp và triển khai")
    g.code("""modal token new                             # đăng nhập tài khoản Modal của đội
modal run modal_app.py::download_weights    # một lần: ~31 GB trọng số Qwen3.8
modal deploy modal_app.py                   # LLM trên 1 GPU H100 (~4 USD/giờ khi chạy)
python -m agqo mandates --llm modal         # gọi LLM thật cho 35 câu thử
modal deploy app/modal_web.py               # triển khai prototype, in ra link công khai""")
    g.p("Phần cứng lượng tử thật (tuỳ chọn): python -m agqo hardware --qasm results/final/circuits/<tệp>.qasm --confirm "
        "(cần token IBM Quantum của đội; lệnh không chạy nếu thiếu --confirm).")

    # ------------------------------------------------------------ 7
    g.h("7. Cấu trúc mã nguồn")
    g.table(["Thư mục / tệp", "Nội dung"], [
        ["agqo/data.py, download.py", "dữ liệu giá, thành phần VN30 theo thời điểm, tải và kiểm tra"],
        ["agqo/portfolio.py, backtest.py, classical.py", "bài toán lô chẵn, QUBO, tài khoản, phí/thuế, các mốc so sánh"],
        ["agqo/insight.py, quantum/", "đặc trưng thị trường và bài toán; mạch QAOA, mô phỏng, thiết kế, xuất Qiskit, phần cứng"],
        ["agqo/llm/, mandate.py", "LLM: dịch yêu cầu, giải thích, kiểm tra số; quy tắc từ khoá"],
        ["agqo/experiment.py, extras.py, stats.py", "huấn luyện 2023, kiểm định 12 quý, kiểm định thống kê"],
        ["agqo/demo.py, app/", "backend và giao diện prototype; triển khai Modal; chụp màn hình"],
        ["modal_app.py", "Qwen3.8-27B trên vLLM, GPU H100"],
        ["results/final, docs/", "kết quả, nhật ký LLM, hình, tài liệu phương pháp, 75 câu hỏi phản biện"],
        ["tests/, submission/", "25 kiểm thử; mã tạo slide, báo cáo, hướng dẫn"]], [6.0, 11.0])

    # ------------------------------------------------------------ 8
    g.h("8. Xử lý sự cố")
    g.table(["Hiện tượng", "Cách xử lý"], [
        ["Trang tải chậm lần đầu", "máy chủ đang khởi động (~10 giây); tải lại trang"],
        ["“Qwen3.8 đang đọc yêu cầu…” lâu", "GPU đang khởi động (~6 phút); kết quả từ khoá vẫn dùng được, LLM tự cập nhật"],
        ["“live LLM budget… used up”", "đã đạt 40 lời gọi/giờ; dùng câu ví dụ hoặc chờ"],
        ["Lỗi “no feasible whole-lot portfolio”", "quy tắc quá chặt với số vốn (ví dụ loại gần hết các ngành); nới quy tắc hoặc tăng vốn"],
        ["Cục bộ: thiếu thư viện", "kích hoạt .venv và chạy lại pip install -r requirements.txt"]], [6.0, 11.0])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    g.d.save(str(OUT))
    return OUT


if __name__ == "__main__":
    print(build())
