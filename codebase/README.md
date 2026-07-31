# VLearn AI Study Agent — README cho `codebase/`

Tài liệu này giải thích **hệ thống này là gì và vận hành như thế nào**, viết
sao cho người không rành kỹ thuật cũng hình dung được. Nếu bạn cần các lệnh
chạy nhanh (cài đặt, khởi động server), xem `CLAUDE.md` ở thư mục gốc repo —
file này tập trung vào **cách nó hoạt động bên trong**.

---

## 1. Tóm tắt trong 3 câu

VLearn AI Study Agent là một "trợ lý học tập" AI: bạn đưa nó một file PDF bài
giảng, rồi hỏi nó bằng tiếng Việt ("tóm tắt giúp tôi", "vẽ sơ đồ tư duy",
"đọc thành audio cho tôi nghe"...). Nó sẽ **tự đọc** đúng những trang cần
thiết trong PDF (không đọc bừa cả tài liệu), rồi tạo ra bản tóm tắt có trích
nguồn trang, sơ đồ tư duy, hoặc file âm thanh — và mọi bước xử lý được hiện
trực tiếp lên màn hình theo thời gian thực, giống như xem AI "suy nghĩ" ngay
trước mắt.

Toàn bộ hệ thống chạy **trên máy cá nhân** (không có server thật trên mạng,
không có tài khoản người dùng, không lưu database) — đây là một bản demo/
prototype cho hackathon, không phải sản phẩm thương mại.

---

## 2. Bức tranh toàn cảnh — 3 mảnh ghép chính

```
┌─────────────────────┐        ┌──────────────────────┐        ┌─────────────────┐
│   Trình duyệt web    │  HTTP  │   Backend (server     │  gọi   │   Các dịch vụ    │
│  (vlearn_clone.html) │ ─────► │   Python chạy máy bạn)│ ─────► │   AI bên ngoài   │
│  Nơi bạn gõ câu hỏi  │ ◄───── │   Đây là "bộ não"     │ ◄───── │  OpenAI (viết)   │
│  và xem kết quả      │ stream │   điều phối mọi thứ   │        │  ElevenLabs (đọc)│
└─────────────────────┘        └──────────────────────┘        └─────────────────┘
```

- **Trình duyệt (frontend):** file `vlearn_clone.html` ở thư mục gốc repo —
  một trang web tĩnh, không cần cài đặt gì, mở trực tiếp bằng Chrome/Edge là
  chạy được. Đây là nơi bạn nhìn thấy khung chat, 3 nút bấm nhanh (Tóm tắt /
  Mind Map / Audio), và kết quả hiện ra.
- **Backend (bộ não):** một chương trình Python chạy ngay trên máy bạn
  (không phải "trên mây"), lắng nghe ở địa chỉ `http://localhost:8000`. Nó
  nhận câu hỏi từ trình duyệt, quyết định phải làm gì, và trả kết quả về.
- **Dịch vụ AI bên ngoài:** backend không tự "biết suy nghĩ" — nó gọi ra
  ngoài Internet tới hai công ty AI: **OpenAI** (mô hình `gpt-4o-mini`) để
  đọc hiểu, viết tóm tắt, và quyết định phải làm gì tiếp theo; **ElevenLabs**
  để chuyển văn bản thành giọng đọc tiếng Việt tự nhiên.

Không có bước nào trong 3 mảnh này bị giả lập (mock) — khi bạn bấm nút, AI
thật sự được gọi, tiền/credit thật sự bị trừ (theo hạn mức free tier).

---

## 3. "AI Agent" nghĩa là gì — và vì sao nó khác một chatbot thường

Một chatbot thông thường chỉ có 1 bước: bạn hỏi → AI trả lời ngay. Hệ thống
này làm việc theo kiểu **agent** — nghĩa là AI được trao một bộ "công cụ"
(tools) và **tự quyết định** dùng công cụ nào, theo thứ tự nào, để hoàn
thành yêu cầu. Nó giống một trợ lý con người hơn là một cái máy trả lời sẵn.

Ví dụ khi bạn gõ **"Tóm tắt tài liệu này giúp tôi, mỗi ý ghi rõ trang"**,
AI tự trải qua các bước sau (và bạn nhìn thấy TỪNG bước này hiện trực tiếp
trên màn hình dưới dạng một dòng nhật ký nhỏ, có dấu ✓ khi xong):

1. **`list_pages`** — "Cho tôi xem tài liệu có bao nhiêu trang, mỗi trang
   nói sơ về cái gì" (giống như liếc qua mục lục trước khi đọc kỹ).
2. **`read_pages`** — AI tự chọn ra những trang có vẻ quan trọng và đọc toàn
   bộ nội dung chữ trong các trang đó (chỉ đọc PHẦN CẦN, không đọc dư).
3. **`emit_summary`** — sau khi đọc xong, AI tự viết bản tóm tắt bằng tiếng
   Việt, ghi rõ mỗi ý lấy từ trang nào (dạng `[Tr.12]`), rồi "xuất bản" bản
   tóm tắt đó lên tab **Tóm tắt** của giao diện.

Nếu bạn hỏi thêm "vẽ sơ đồ tư duy" trong cùng câu, AI sẽ gọi thêm
**`emit_mindmap`** trong CÙNG một lượt xử lý — không cần đọc lại tài liệu
từ đầu, vì nó đã nhớ nội dung vừa đọc ở bước 2.

Nếu bạn hỏi audio, nó gọi **`render_audio`**: viết một đoạn kịch bản đọc tự
nhiên (không phải đọc nguyên bản tóm tắt khô khan), rồi gửi đoạn kịch bản đó
sang ElevenLabs để tạo file mp3 thật.

**Quan trọng:** 5 "công cụ" này (`list_pages`, `read_pages`, `emit_summary`,
`emit_mindmap`, `render_audio`) **không hề chứa AI bên trong** — chúng chỉ
là các hàm lập trình thuần tuý (đọc file, kiểm tra định dạng, lưu file mp3).
Phần "thông minh" — quyết định đọc trang nào, viết tóm tắt ra sao, sơ đồ nên
chia nhánh thế nào — **nằm hoàn toàn trong đầu AI của OpenAI**, được gọi qua
duy nhất một chỗ trong code (`agent.py`). Tách bạch như vậy để dễ kiểm soát:
nếu tool trả kết quả sai định dạng, đó là lỗi code sửa được; nếu nội dung
tóm tắt tệ, đó là vấn đề của AI, cần sửa cách "ra lệnh" cho nó (gọi là
prompt), không phải sửa code.

AI được giới hạn tối đa **8 vòng lặp** (đọc → suy nghĩ → gọi công cụ) cho
mỗi câu hỏi, để tránh trường hợp nó "loay hoay" mãi không dừng.

---

## 4. Đi theo một yêu cầu cụ thể, từng bước một

Giả sử bạn gõ vào ô chat: **"Đọc tóm tắt tài liệu này thành podcast cho tôi
nghe"**. Đây là toàn bộ hành trình:

1. **Trình duyệt** gửi câu hỏi đó tới backend qua một kết nối đặc biệt gọi là
   *Server-Sent Events (SSE)* — hiểu đơn giản là một đường dây mở, cho phép
   backend gửi về NHIỀU tin nhắn nhỏ liên tục thay vì phải đợi xong hết mới
   trả lời một lần. Đây là lý do bạn thấy các dòng trạng thái hiện ra dần
   dần thay vì cả trang bị "đứng hình" chờ.
2. **Backend** (`server.py`) nhận câu hỏi, chuyển cho "vòng lặp agent"
   (`agent.py`) xử lý.
3. Agent gọi OpenAI, OpenAI quyết định: cần đọc tài liệu trước
   (`list_pages` → `read_pages`), sau đó viết một kịch bản đọc ngắn (300-500
   từ, văn nói tự nhiên, không có ký hiệu trích trang vì đọc lên sẽ kỳ) và
   gọi `render_audio`.
4. `render_audio` gửi đoạn kịch bản đó sang **ElevenLabs**, nhận về file âm
   thanh (mp3), lưu vào thư mục `codebase/audio_output/` trên máy bạn.
5. Backend gửi về trình duyệt một sự kiện "đã có audio, đây là đường link",
   trình duyệt tự động mở tab **Audio** và bạn có thể bấm nghe ngay.
6. Mỗi bước 2-5 đều được stream về trình duyệt NGAY khi xảy ra — không phải
   đợi tới bước cuối mới thấy gì.

**Một chi tiết tiết kiệm chi phí đáng chú ý:** file mp3 được đặt tên theo
"dấu vân tay" (hash) của chính nội dung kịch bản. Nghĩa là nếu kịch bản y
hệt được yêu cầu lại lần hai, hệ thống nhận ra đã có sẵn file rồi, dùng lại
luôn thay vì gọi ElevenLabs lần nữa — vì gói miễn phí của ElevenLabs có hạn
mức (khoảng 10.000 ký tự/tháng), tránh lãng phí khi test đi test lại hoặc
demo trùng lặp.

---

## 5. Bản đồ code — mỗi file làm gì

| File | Vai trò | Có gọi AI không? |
|---|---|---|
| `server.py` | "Cổng vào" — nhận yêu cầu HTTP từ trình duyệt, kiểm tra key API lúc khởi động, phát trực tiếp (stream) kết quả về. Có đúng 1 endpoint xử lý việc thật: `POST /api/agent`. | Không |
| `agent.py` | "Bộ não điều phối" — vòng lặp gọi OpenAI, quyết định gọi công cụ nào, khi nào dừng. **Đây là nơi DUY NHẤT trong toàn hệ thống gọi mô hình ngôn ngữ (LLM) để suy nghĩ.** | **Có** (OpenAI `gpt-4o-mini`) |
| `tools.py` | 5 "công cụ" agent có thể dùng: đọc mục lục, đọc trang, xuất tóm tắt, xuất sơ đồ, tạo audio. Cũng có bộ kiểm tra sơ đồ tư duy (không cho sơ đồ bịa số trang, quá ít nhánh, hoặc quá sâu). | Không (thuần logic) |
| `pdf_parser.py` | Mở file PDF, tách text ra theo từng trang. | Không |
| `tts.py` | Gọi ElevenLabs để biến văn bản thành giọng đọc, có cơ chế cache theo nội dung để đỡ tốn credit. | **Có** (ElevenLabs) |
| `conftest.py` | File kỹ thuật giúp bộ kiểm thử (test) tìm thấy code — không có logic gì. | Không |
| `tests/` | Các bài kiểm thử tự động, đảm bảo mỗi phần code hoạt động đúng. Test **không bao giờ** gọi AI thật (luôn giả lập/mô phỏng) — để chạy nhanh, miễn phí, và không phụ thuộc mạng. | Không |
| `scripts/try_voices.py` | Script dùng một lần để nghe thử các giọng đọc tiếng Việt của ElevenLabs và chọn ra giọng phù hợp nhất (đã chọn xong, không cần chạy lại). | Có (chỉ chạy tay, không nằm trong luồng chính) |

Ở thư mục gốc repo (ngoài `codebase/`) còn có:

- **`vlearn_clone.html`** — toàn bộ giao diện người dùng, một file HTML/CSS/
  JavaScript duy nhất, không cần cài đặt hay "build" gì. Mở thẳng bằng trình
  duyệt là chạy.
- **`eval/`** — bộ câu hỏi mẫu ("golden set") cùng script tự động chạy thử
  hệ thống với 10 câu hỏi khác nhau và chấm điểm kết quả bằng các phép kiểm
  tra máy móc (ví dụ: có trích trang thật không, sơ đồ có đủ nhánh không...).
  Dùng để đo chất lượng hệ thống một cách khách quan, không chỉ "nhìn qua thấy
  ổn".

---

## 6. Vì sao thiết kế theo kiểu này? (Các quyết định quan trọng, giải thích lý do)

- **Chỉ một cửa vào cho AI (`agent.py`):** dù bạn bấm nút hay gõ chat, dù
  bạn hỏi tóm tắt hay audio, tất cả đều đi qua đúng MỘT vòng lặp AI duy nhất.
  Ba nút bấm nhanh (📝 Tóm tắt / 🧠 Mind Map / 🎧 Audio) thực chất chỉ là
  "điền sẵn" một câu hỏi mẫu vào ô chat rồi gửi đi giống hệt như bạn tự gõ —
  không có đường tắt xử lý riêng nào phía sau. Điều này đảm bảo hành vi nhất
  quán: sửa một chỗ là sửa cho mọi cách gọi.
- **Công cụ (tools) không chứa AI:** giúp tách rõ "lỗi do logic lập trình"
  (sửa code) và "lỗi do AI suy nghĩ sai" (sửa cách ra lệnh cho AI — prompt).
  Nếu gộp chung, rất khó biết khi nào cần sửa gì.
- **Giới hạn 8 vòng lặp:** nếu không giới hạn, một câu hỏi khó hiểu có thể
  khiến AI loay hoay gọi công cụ vô tận, tốn tiền và không bao giờ trả lời.
- **Kiểm tra sơ đồ tư duy bằng code thuần (`validate_mindmap`), không nhờ AI
  tự chấm:** máy móc kiểm tra 3 lỗi cụ thể — trích trang không có thật (AI
  "bịa" nguồn), sơ đồ có quá ít nhánh chính (AI lười, gộp hết thành 1-2 dòng
  phẳng), hoặc quá sâu (khó đọc trên giao diện). Việc này không cần AI vì đó
  là những quy tắc rõ ràng, đếm được — dùng code cho rẻ, nhanh, và luôn nhất
  quán.
- **Kết quả stream từng bước thay vì chờ xong mới hiện:** với các thao tác
  mất vài giây tới vài chục giây (agent phải đọc, suy nghĩ, có khi gọi
  ElevenLabs), nếu bắt người dùng nhìn màn hình trắng chờ sẽ cảm giác "đứng
  hình"/lỗi. Hiện tiến trình theo thời gian thực giúp người dùng tin tưởng
  hệ thống đang thực sự hoạt động.
- **Cache audio theo nội dung:** ElevenLabs miễn phí có hạn mức thấp. Nếu
  không cache, demo đi demo lại hoặc test nhiều lần rất dễ hết hạn mức giữa
  chừng.
- **Chạy hoàn toàn trên máy cá nhân (localhost), không có server công khai:**
  đây là bản chứng minh ý tưởng (prototype) cho hackathon, không phải sản
  phẩm triển khai thật — không có đăng nhập, không có nhiều người dùng cùng
  lúc, không có cơ sở dữ liệu lưu trữ lâu dài.

---

## 7. Những giới hạn cần biết (nói thẳng, không tô hồng)

- **Không có trí nhớ giữa các phiên:** đóng trình duyệt lại là mất hết đoạn
  chat — hệ thống không lưu lịch sử vào đâu cả.
- **Chỉ xử lý được MỘT tài liệu PDF tại một thời điểm** — tài liệu đang mở
  được cấu hình sẵn trong `server.py` (biến `PDF_PATH`), không có tính năng
  tải lên PDF khác qua giao diện.
- **AI có thể trích dẫn sai trang trong một số trường hợp hiếm** — hệ thống
  có kiểm tra tự động để bắt lỗi này (xem mục 6), nhưng không phải 100% các
  câu trả lời tự do (chat) đều được kiểm tra chặt như tóm tắt/sơ đồ.
- **Cần Internet và 2 API key hợp lệ (OpenAI + ElevenLabs)** để chạy — nếu
  thiếu, `server.py` sẽ từ chối khởi động và báo rõ thiếu key nào, thay vì
  chạy lỗi nửa chừng giữa demo.
- **Không có xác thực người dùng (authentication)** — bất kỳ ai truy cập
  được `http://localhost:8000` trên máy đang chạy server đều dùng được toàn
  bộ tính năng. Chấp nhận được vì đây là demo chạy local, không public.

---

## 8. Muốn tìm hiểu sâu hơn thì đọc gì?

- Muốn biết **cách chạy hệ thống từng bước** (cài đặt, lệnh, mở trình duyệt):
  xem `CLAUDE.md` ở thư mục gốc repo, mục "Commands".
- Muốn biết **toàn bộ quyết định thiết kế và lý do đằng sau**, kể cả những
  cái đã cân nhắc rồi bỏ: xem
  `docs/superpowers/plans/2026-07-30-vlearn-ai-study-agent.md` (kế hoạch xây
  dựng chi tiết, có giải thích từng bước) và file spec thiết kế đi kèm trong
  `docs/superpowers/specs/`.
- Muốn biết **hệ thống hoạt động tốt tới đâu, đo bằng số liệu**: xem thư mục
  `eval/` — có bộ câu hỏi mẫu và bảng kết quả chấm tự động.
