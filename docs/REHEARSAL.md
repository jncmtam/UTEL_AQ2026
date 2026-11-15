# Rehearsal: the five hardest questions

Each card has the question as a judge will likely ask it, a 20-second answer in English and Vietnamese,
the numbers and figure to point at, the follow-up you should expect, and what **not** to say.
Full detail is in [QA.md](QA.md); every number here comes from `results/final/`.

**One pattern for all five: concede → number → reframe.**
1. *Concede* in the first sentence. Judges trust a team that says "yes, and we measured it".
2. *Number*: give the exact figure and the test behind it.
3. *Reframe*: say what the result means for the claim you *do* make.

Never argue with a negative result. It is on the evaluation board ([A8](figures/A8_evaluation_board.png))
because we chose to put it there.

---

## 1. "So there is no quantum advantage. Why use a quantum computer at all?"

**Answer (EN, 20 s).** Correct, and we say so on the first page. At 16 qubits, exact enumeration solves
the problem in 0.12 seconds. What we claim is a *method*: a circuit written from the data that beats
its own classical starting point 6.9× and textbook QAOA 19×, in 12 out of 12 unseen quarters. We built
it so the comparison stays honest as the problem grows. Enumeration grows as 2ⁿ, the circuit as n².

**Trả lời (VI, 20 giây).** Đúng vậy, và chúng em nói rõ ngay trang đầu. Với 16 qubit, liệt kê toàn bộ chỉ
mất 0,12 giây. Điều chúng em khẳng định là một *phương pháp*: mạch được thiết kế từ dữ liệu, vượt trạng
thái khởi động cổ điển của chính nó 6,9 lần và QAOA sách giáo khoa 19 lần, trong cả 12/12 quý chưa từng
thấy. Chúng em xây dựng để phép so sánh vẫn trung thực khi bài toán lớn lên: liệt kê tăng theo 2ⁿ, mạch chỉ
tăng theo n².

**Point at:** [A6 scaling](figures/A6_scaling.png) (left: 2ⁿ vs n²; right: gain over warm start grows
4.3× → 16.7× from 8 to 20 qubits) and [05](figures/05_quantum_test.png).

**Expected follow-up: "When would it be useful then?"** At a full VN30 register (30 stocks × 2 lots ≈ 60
qubits), enumeration at our measured rate would take about 10⁵ years. On hardware, only shallow circuits
survive today: our noise-aware circuit (16 CZ gates) keeps 1.6× its warm start under IBM Heron noise.
The deep one would need two-qubit errors about 11× lower than today's 0.18 %. We would still have to beat
simulated annealing at that size, and we say so.

**Don't say:** "quantum speed-up", "quantum is faster", "this will beat classical soon". Don't dismiss
annealing: one short run is already within 5 % of the optimum in 12/12 quarters.

---

## 2. "A simple greedy algorithm gets almost the same result. What does your method add?"

**Answer (EN).** Yes, and we added that baseline ourselves because it is the strongest simple one. At
20M VND, greedy lot filling reaches 7.5 % tracking error against our 6.8 %, and naive rounding 12.1 %. So
most of the gain comes from optimising the lot decision at all. Solving it exactly adds 0.7 points
quarterly, which is borderline (CI −1.53 to +0.02), and 1.3 points with monthly rebalancing, which is
significant. The other things greedy cannot do: it cannot guarantee personal caps (we get 0 violations
by construction), it does not tell you how far it is from the optimum, and it tends to concentrate.
In the latest example it put 36 % of the account in one stock.

**Trả lời (VI).** Đúng, và chính chúng em đã thêm baseline này vì nó là phương pháp đơn giản mạnh nhất. Với
tài khoản 20 triệu, thuật toán tham lam đạt sai số bám 7,5 %, AGQO 6,8 %, làm tròn thông thường 12,1 %. Vậy
phần lớn lợi ích đến từ việc *tối ưu quyết định lô*. Giải chính xác thêm 0,7 điểm khi tái cân bằng theo quý
(sát ngưỡng ý nghĩa) và 1,3 điểm khi tái cân bằng theo tháng (có ý nghĩa thống kê). Thêm nữa, AGQO bảo đảm
mọi giới hạn cá nhân (0 vi phạm), biết chính xác khoảng cách tới tối ưu, và không dồn tiền vào một mã như
thuật toán tham lam (36 % vào MWG trong ví dụ mới nhất).

**Point at:** [A7 robustness](figures/A7_robustness.png) (amber squares) and [A4](figures/A4_one_decision.png).

**Expected follow-up: "But greedy earned 26 %/yr at 20M and you earned 16 %."** That return came from
one concentrated bet that happened to pay off over 12 quarters. Its tracking error is higher (7.5 % vs
6.8 %). The investor asked to follow VN30, not to bet on MWG. With one or two lots per stock, realised
returns at 20M range from 12 % to 26 % mostly by luck, which is why we judge by tracking error with
paired bootstrap intervals.

**Don't say:** "greedy is bad" or "AGQO is much better than greedy". At 100M VND they are statistically
the same.

---

## 3. "Vietnam allows odd lots since 2022. Why not just buy 1-share lots?"

**Answer (EN).** We tested it, and odd lots track better: 2.5 % tracking error at 20M against 6.8 % for
whole lots. They also return more, as long as the odd-lot part costs less than about 6.8 % extra at 20M
or 2.6 % at 100M. What we cannot model is fill risk: the odd-lot book is separate, thinner, and takes
limit orders only. So odd lots are a real alternative, and our next version adds "whole lots plus an
odd-lot top-up" as a register option. AGQO is the tool when odd-lot liquidity is poor, when a broker
charges a minimum fee per order, or when the investor wants board-lot orders only.

**Trả lời (VI).** Chúng em đã kiểm tra: lô lẻ bám chỉ số tốt hơn (sai số 2,5 % so với 6,8 % ở tài khoản 20
triệu) và lợi nhuận cao hơn, miễn là chi phí thêm cho phần lô lẻ dưới khoảng 6,8 % (20 triệu) hoặc 2,6 %
(100 triệu). Điều chúng em chưa mô hình được là rủi ro không khớp lệnh: sổ lệnh lô lẻ tách riêng, mỏng hơn,
chỉ nhận lệnh giới hạn. Vì vậy lô lẻ là một lựa chọn thực sự, và phiên bản tiếp theo sẽ thêm "lô chẵn + bù
lô lẻ" vào thanh ghi qubit. AGQO phù hợp khi thanh khoản lô lẻ kém, khi công ty chứng khoán thu phí tối
thiểu mỗi lệnh, hoặc khi nhà đầu tư chỉ muốn đặt lệnh lô chẵn.

**Point at:** [A7](figures/A7_robustness.png), right panel (lines cross zero at the break-even cost).

**Expected follow-up: "What is the real odd-lot spread?"** We did not measure it; it needs order-book data
we don't have. That is why we report a break-even curve instead of one number. The judge can read off
the answer for any spread they believe.

**Don't say:** "odd lots are illiquid so they don't count". We showed they win under reasonable costs.

---

## 4. "Your learned AI model doesn't beat a single fixed schedule. So where is the AI?"

**Answer (EN).** Right: on test, the learned schedule wins only 7 of 12 quarters against a frozen one
(p = 0.47), and the training-chosen polish didn't help either. We report both as "no gain". The AI that
matters is in three places. First, the circuit design rules read the data: warm start, aligned mixer,
coupling pruning and scaling. That structure is what beats textbook QAOA 19×. Second, the LLM turns
Vietnamese instructions into exact constraints, 35/35 against 68.6 % for keyword rules. Third, the same
guidance becomes decisive on hardware. Choosing for *noisy* success picks a 16-gate circuit that keeps
1.6× its warm start. The noiseless choice collapses to random guessing.

**Trả lời (VI).** Đúng: trên dữ liệu kiểm tra, mô hình học chỉ thắng lịch cố định 7/12 quý (p = 0,47), và
bước tinh chỉnh chọn trên dữ liệu huấn luyện cũng không giúp. Chúng em báo cáo cả hai là "không có lợi
ích". AI thực sự quan trọng ở ba chỗ. Một, các quy tắc thiết kế mạch đọc từ dữ liệu (khởi động ấm, mixer
căn chỉnh, cắt bớt liên kết, chuẩn hóa), chính cấu trúc này vượt QAOA sách giáo khoa 19 lần. Hai, LLM chuyển
yêu cầu tiếng Việt thành ràng buộc chính xác (35/35 so với 68,6 %). Ba, cùng cơ chế hướng dẫn đó trở nên
quyết định trên phần cứng: chọn theo thành công *khi có nhiễu* ra mạch 16 cổng giữ 1,6 lần lợi thế, còn
lựa chọn không tính nhiễu sụp về mức ngẫu nhiên.

**Point at:** [04](figures/04_ai_guidance.png) (CV is close: 16.1 % vs 15.7 %), then
[A5 hardware](figures/A5_hardware.png).

**Expected follow-up: "Isn't k-NN too simple to call AI?"** It is supervised learning chosen by
cross-validation. That is the same idea as parameter transfer in the QAOA literature (Galda 2021,
Shaydulin 2023). With 48 training problems, a small auditable model is the right size; a deep network
would overfit.

**Don't say:** "the model is AI-powered" without numbers, or hide that the oracle (25.2 %) is only a bit
above frozen (23.8 %).

---

## 5. "The VN30 ETF returned more. Why would anyone use this?"

**Answer (EN).** For an investor without personal rules, the ETF is the right product, and we say so.
E1VFVN30 returned about 1.1 % a year more: it is cheaper to hold and reinvests dividends. AGQO is for the
investor the ETF cannot serve. That means someone who excludes real estate, caps banks at 30 %, limits the
number of stocks, or wants to own shares directly. Under those rules we have 0 violations, and we show the
cost of each rule: +3.8 points of tracking error for "no real estate, banks ≤ 30 %". Also, AGQO tracks the
VN30 *index* more closely than the ETF's *traded price* (weekly 3.2 % vs 5.2 %).

**Trả lời (VI).** Với nhà đầu tư không có quy tắc riêng, ETF là lựa chọn đúng, và chúng em nói rõ điều đó.
E1VFVN30 có lợi nhuận cao hơn khoảng 1,1 %/năm vì chi phí nắm giữ thấp hơn và tái đầu tư cổ tức. AGQO dành
cho nhà đầu tư mà ETF không phục vụ được: muốn loại bất động sản, giới hạn ngân hàng 30 %, giới hạn số mã,
hoặc muốn trực tiếp sở hữu cổ phiếu. Với các quy tắc đó, AGQO không vi phạm lần nào, và cho thấy cái giá của
từng quy tắc (+3,8 điểm sai số bám cho "không bất động sản, ngân hàng ≤ 30 %"). Ngoài ra AGQO bám *chỉ số*
VN30 sát hơn *giá giao dịch* của ETF (theo tuần 3,2 % so với 5,2 %).

**Point at:** [09 vs ETF](figures/09_vs_etf.png), then [10 mandates](figures/10_mandates.png).

**Expected follow-up: "How big is that market really?"** Vietnam had over 14.3 million domestic individual
securities accounts at the end of October 2026 (VSDC). Small accounts are where lots matter most: at
20M VND, naive rounding leaves most of the money in cash.

**Don't say:** "AGQO beats the ETF". It doesn't on return, and the board says "trails".

---

## Bonus: "Can the LLM hallucinate a number to the investor?"

**Answer (EN).** It can write one, but it cannot show one. Every number in an explanation must exist in
the evidence pack that code builds, and every trade note must match an executed trade. A meaning check
also requires each tracking error to be stated against VN30. When we added that check, our first prompt
failed it 0/12: the numbers were right but the references were wrong. We renamed the evidence fields to
carry their reference and re-ran: numbers 12/12, meaning 11/12. The one flag is shown, not hidden.

**Trả lời (VI).** Mô hình có thể viết sai, nhưng không thể hiển thị sai: mọi con số phải có trong gói bằng
chứng do code tạo ra, mọi ghi chú giao dịch phải khớp lệnh đã thực hiện, và kiểm tra ý nghĩa bắt buộc sai
số bám phải được nói là "so với chỉ số VN30". Khi thêm kiểm tra này, prompt đầu tiên trượt 0/12 (số đúng
nhưng tham chiếu sai). Chúng em đổi tên trường bằng chứng để ghi rõ tham chiếu và chạy lại: số liệu 12/12,
ý nghĩa 11/12; trường hợp còn lại được hiển thị, không che giấu.

---

## Drill

1. Read each English answer aloud with a timer: under 25 seconds.
2. Have a teammate ask each question with a hostile twist ("Isn't this just…?"). Answer with the same
   three moves.
3. For every number you say, know which figure shows it.
4. Practise the follow-ups more than the first answers. Judges decide on the second question.
