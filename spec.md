# AI SPEC - VLearn AI Study Agent · Nhóm E402 · Zone [TODO]
Hướng: [x] A - VLearn  [ ] B - Trợ lý Học viên  [ ] C - Làn mở
Loại: [ ] Tối ưu tính năng có sẵn  [x] Tính năng mới

## §1. User & Job

- Job executor + workflow:
  - Job executor: học viên VLearn đang ôn lại bài giảng sau buổi học hoặc trước quiz/lab.
  - Workflow hiện tại: mở lại slide/transcript/video, tự tìm phần liên quan, hỏi tutor/chatbot nếu bí, sau đó tự gom ý thành ghi chú học tập.

- Core JTBD:
  - Khi cần ôn lại một bài giảng dài, học viên muốn nhanh chóng nắm lại các ý chính và biết ý đó nằm ở đâu trong tài liệu, để có thể học tiếp hoặc chuẩn bị làm bài mà không phải tự lục từng trang.

- Problem statement:
  - Học viên mất thời gian tìm lại nội dung quan trọng trong tài liệu bài giảng dài; khi nhận câu trả lời không có căn cứ trang rõ ràng, họ khó biết nên tin hay phải kiểm lại ở đâu.

- Evidence:
  - Số liệu khảo sát/phỏng vấn:
    - Khảo sát 44 người học viên.
    - Trong đó có 93.2% học viên, còn lại là lab-coach
    - 32/44 (72.7%) người khảo sát cho biết họ "Rất thường xuyên" hoặc "thường xuyên" phải đọc và tóm tắt nội dung từ slide học tập
    - 28/44 (63.6%) người khảo sát cho biết họ thấy slides có quá nhiều nội dung.

## §2. Impact & quyết định chọn

| Ứng viên | Bao nhiêu người gặp | Tần suất | Tốn gì mỗi lần | Khả thi trong hackathon | Quyết định |
|---|---:|---|---|---|---|
| Tóm tắt tài liệu có trích trang | 35; thực hiện khảo sát | Sau mỗi buổi học / trước quiz | Mất thời gian lục slide; khó kiểm chứng khi không có citation | Cao: đã có PDF parser + agent + summary tool | Chọn |
| Sơ đồ tư duy từ bài giảng | 34 | Khi cần hệ thống hóa kiến thức | Dễ bỏ sót mối quan hệ giữa các ý | Cao: output Markdown/Markmap, kiểm tra được nhánh/trang | Chọn như output phụ |
| Audio/podcast ôn bài | 34 | Khi muốn nghe lại lúc di chuyển | Nếu đọc nguyên slide thì khô, mất tập trung | Trung bình: cần ElevenLabs key | Chọn như output phụ |
| Upload nhiều PDF / quản lý thư viện tài liệu | 30 | Ít hơn trong demo một tài liệu | Cần storage, auth, UI quản lý | Thấp trong 1.5 ngày | Loại |
| Chat tutor tự do mọi chủ đề | 40 | Cao | Sai kiến thức ngoài tài liệu sẽ làm mất niềm tin | Rủi ro cao nếu không grounding chặt | Loại khỏi lát cắt |

- Ứng viên đã loại:
  - Upload nhiều PDF / thư viện tài liệu: vượt phạm vi prototype local, cần storage và quản lý trạng thái.
  - Chat tutor tự do mọi chủ đề: chi phí lỗi cao vì dễ trả lời ngoài tài liệu hoặc bịa kiến thức.

- Ứng viên chọn:
  - Agent đọc một PDF bài giảng đã cấu hình sẵn và tạo summary/mind map/audio có căn cứ. Lựa chọn này bám vào pain  point của người phỏng vấn và build được end-to-end trong hackathon.

## §3. Giải pháp tương tự đã nghiên cứu

- NotebookLM:
  - Flow: user đưa tài liệu nguồn, hỏi đáp/tóm tắt dựa trên nguồn, kết quả thường đi kèm grounding.
  - Đáng học: ưu tiên trả lời trong phạm vi tài liệu user đã chọn.
  - Đáng né: cảm giác như một sản phẩm riêng, không gắn vào flow VLearn hiện tại.
  - Mình khác gì: gắn trực tiếp vào giao diện VLearn clone và stream từng tool call để học viên thấy agent đang đọc gì/làm gì.

- ChatGPT / Study mode:
  - Flow: user hỏi tự do, AI giải thích theo hội thoại.
  - Đáng học: ngôn ngữ linh hoạt, hiểu nhiều kiểu yêu cầu khác nhau.
  - Đáng né: nếu không ép grounding theo tài liệu, dễ trả lời quá rộng hoặc không có trang nguồn.
  - Mình khác gì: agent chỉ đọc PDF đã cấu hình và output chính phải có citation/mind map/audio theo tool.

- Quizlet AI / công cụ học tập dạng flashcard:
  - Flow: biến tài liệu thành học liệu phụ trợ.
  - Đáng học: output học tập nên ngắn, dễ dùng ngay.
  - Đáng né: tách rời khỏi tài liệu gốc làm user khó kiểm chứng.
  - Mình khác gì: tập trung vào "ôn lại bài giảng này" với nguồn trang rõ ràng, chưa mở rộng sang quiz/flashcard.

## §4. Thiết kế

- Lát cắt một câu:
  - Một học viên đang ôn lại một PDF bài giảng trong VLearn yêu cầu tóm tắt/mind map/audio; AI quyết định cần đọc những trang nào bằng tool `list_pages` và `read_pages`; hệ thống trả về kết quả học tập có căn cứ và stream tiến trình xử lý trực tiếp trên giao diện.

- Non-goals:
  - Không build upload/chọn nhiều PDF qua giao diện.
  - Không build đăng nhập, phân quyền, database hay lưu lịch sử chat dài hạn.
  - Không trả lời kiến thức ngoài tài liệu như một general tutor.
  - Không tự chấm điểm học viên hoặc sinh quiz bắt buộc.
  - Không public deploy; demo chạy local.

- Mức prototype nhắm tới:
  - [ ] Sketch  [ ] Mock  [x] Working
  - Phần thật: frontend `vlearn_clone.html`, backend FastAPI, SSE streaming, OpenAI `gpt-4o-mini`, PDF parsing, agent tools, mind map validation, ElevenLabs TTS, audio cache.
  - Phần mock/stub khi test: test tự động không gọi AI thật; `eval/results-20260731-005124.md` chạy với `TTS_MODE=stub` để tránh tốn credit và phụ thuộc mạng.

- Automation:
  - [ ] augment  [x] conditional  [ ] automate
  - Lý do theo cost-of-error: summary/mind map/audio có thể tự tạo khi có căn cứ trong PDF; nếu thiếu trang, ngoài phạm vi, hoặc không đủ căn cứ thì agent phải thu hẹp phạm vi/không bịa. Sai kiến thức làm học viên học sai và mất niềm tin, nên không chọn automate toàn phần.

- §4b. Nguyên tắc đã áp dụng:

| Nguyên tắc | Áp cụ thể vào đâu trong prototype |
|---|---|
| G1 - Làm rõ hệ thống làm được gì | UI có 3 hành động nhanh: Tóm tắt / Mind Map / Audio; backend chỉ có một endpoint agent cho đúng phạm vi tài liệu. |
| G2 - Làm rõ nó làm tốt đến đâu | Summary yêu cầu citation dạng `[Tr.x]`; mind map được validate trang hợp lệ, đủ nhánh, không quá sâu. |
| G10 - Thu hẹp phạm vi khi nghi ngờ | Case như "trang 999" hoặc câu hỏi ngoài tài liệu phải xử lý không lỗi và không bịa trang. |
| G11 - Giải thích vì sao | Agent stream các bước tool call (`list_pages`, `read_pages`, `emit_summary`,...) để user thấy vì sao kết quả được tạo ra. |
| PAIR - Explainability + Trust | Kết quả gắn với trang nguồn và trace tiến trình để user kiểm chứng thay vì chỉ tin vào câu trả lời cuối. |
| PAIR - Feedback + Control | User luôn có thể hỏi lại/sửa yêu cầu ngay trong ô chat; các nút nhanh chỉ là prompt mẫu, không khóa flow. |

## §5. Kiểu lỗi - 4 lớp chỗ khó + kịch bản

| Kịch bản | Lớp | Hành vi mong muốn | Nguyên tắc |
|---|---|---|---|
| User yêu cầu tóm tắt nhưng agent không đọc trang nào | ① Nguồn sự thật | Gọi `list_pages`/`read_pages` trước khi `emit_summary`; nếu không có nội dung thì báo không đủ căn cứ | G2, G10 |
| Summary không có citation trang | ① Nguồn sự thật | Trả summary có `[Tr.x]`; case S01 đang là failure cần sửa prompt/check | G2, PAIR Trust |
| Mind map ghi trang không tồn tại | ① Nguồn sự thật | `validate_mindmap` chặn trang bịa và yêu cầu agent sửa | G2 |
| User hỏi "tóm tắt trang 999" | ② Mơ hồ/thiếu thông tin | Không crash, báo tài liệu không có trang đó và gợi ý xem các trang hợp lệ | G10 |
| User yêu cầu "giải thích định lý Pythagore trong tài liệu này" nhưng PDF không có | ② Mơ hồ/thiếu thông tin | Nói không thấy căn cứ trong tài liệu; không tạo citation giả | G10, G11 |
| User yêu cầu làm bài tập/quiz thay mình | ③ Ngoài phạm vi/thẩm quyền | Từ chối làm thay, có thể gợi ý ôn lại phần liên quan trong tài liệu | G1, G10 |
| User yêu cầu upload PDF khác | ③ Ngoài phạm vi/thẩm quyền | Nói prototype chỉ dùng một PDF đã cấu hình; không giả vờ đã đọc file mới | G1 |
| Audio đọc cả ký hiệu citation làm khó nghe | ④ Đặc thù domain | `render_audio` tạo script văn nói, không đọc `[Tr.x]` | G5 |
| Mind map quá sâu hoặc quá ít nhánh | ④ Đặc thù domain | Validate tối thiểu 3 nhánh chính và độ sâu tối đa 4 để dễ đọc | G2 |
| Agent lặp tool quá nhiều gây tốn tiền/chờ lâu | ④ Đặc thù domain | Dừng ở `MAX_ITERATIONS = 8`, stream trạng thái để user biết hệ thống còn chạy | G11 |

## §6. Bốn đường đi của trải nghiệm

- Happy path:
  - User bấm "Tóm tắt" hoặc hỏi "Cho tôi các ý chính"; agent liệt kê trang, đọc trang cần thiết, xuất summary có citation, UI mở tab Tóm tắt.

- Low-confidence:
  - User hỏi mơ hồ hoặc yêu cầu một phần chưa xác định rõ; agent đọc mục lục/trang liên quan trước, trả lời kèm giới hạn "dựa trên các trang đã đọc".

- Failure/không căn cứ:
  - User hỏi trang không tồn tại hoặc nội dung ngoài tài liệu; hệ thống không bịa, không tạo nguồn giả, trả lời rằng không có căn cứ trong PDF hiện tại.

- Correction:
  - User sửa yêu cầu trong chat như "ngắn hơn", "thêm sơ đồ", "chỉ tập trung phần X"; agent dùng cùng endpoint và có thể gọi thêm tool phù hợp trong cùng flow.

- Khi bị đòi ngoài phạm vi:
  - Với upload PDF khác, lưu lịch sử, hay hỏi general knowledge, prototype nói rõ giới hạn: bản demo local chỉ xử lý một PDF bài giảng đã cấu hình.

- Case đặc thù domain:
  - Audio phải là văn nói tiếng Việt tự nhiên, không đọc raw citation; mind map phải có trang hợp lệ để học viên quay lại slide kiểm chứng.

## §7. Kiểm thử

- Chiều chất lượng + định nghĩa kiểm chứng được:
  - Grounded summary: summary không rỗng và có ít nhất một citation `[Tr.x]` hợp lệ.
  - Mind map hữu dụng: mọi trang hợp lệ, có ít nhất 3 nhánh chính, độ sâu không quá 4.
  - Agent control: không lỗi và không vượt giới hạn 8 vòng lặp.
  - Audio usable: có file/script audio và script không chứa marker trang khó nghe.
  - Không bịa nguồn: với câu hỏi ngoài phạm vi, không tạo summary page/citation giả.

- Golden set:
  - File hiện có: `eval/golden_set.json`.
  - Hiện trạng: 10 case, gồm summary S01-S02, mind map M01-M02, combo C01-C02, audio A01, edge E01-E03.
  - TODO để đạt rubric: mở rộng lên >=20 case, phủ >=2 case cho mỗi lớp chỗ khó, 8-10 case thường, 2-4 case hiếm, và >=10 case lấy/phát triển từ chatlog thật.

- Quality bar:
  - Đạt khi >=90% phép kiểm qua toàn bộ golden set, và không có lỗi cứng: crash endpoint, citation trang không tồn tại trong mind map, audio không tạo được ở happy path, hoặc agent vượt 8 vòng lặp.

- Kết quả các lượt chạy:

| Lượt chạy | File | Cấu hình | Kết quả | Ghi chú |
|---|---|---|---:|---|
| 2026-07-31 00:51:24 | `eval/results-20260731-005124.md` | `TTS_MODE=stub`, model `gpt-4o-mini` | 36/37 = 97.3% | Fail duy nhất: S01 thiếu citation trang |

## §8. Phân công & kế hoạch

- Phân công có tên:
  - Spec: Lê Văn Tuệ - 2A202601048.
  - Evidence/mining/survey: Trương Đan Vi - 2A202601178.
  - Prompt/agent behavior: Hồ Trọng Hảo - 2A202601358
  - Code/backend/frontend: Trần Mạnh Hùng - 2A202601058.
  - Demo/slides/validation: Nguyễn Cảnh Hoàng - 2A202601588.

- Willing users + kế hoạch validation CP5:
  - Willing users: thành viên nhóm khác
  - Kế hoạch validation: mỗi người làm một task thật trong 10 phút: "hãy dùng prototype để ôn lại bài giảng này"; quan sát không gợi ý; hỏi 3 câu:
    1. Điều gì khó hiểu hoặc khó chịu nhất?
    2. Kết quả này bạn có tin không - vì sao?
    3. Bạn có dùng thật không - vì sao / vì sao chưa?
  - Log vào `validation/` theo bảng: người thử, task, quan sát, quote nguyên văn, mức nghiêm trọng.

- Multi-prototype:
  - Trục khác biệt đã cân nhắc: nhiều endpoint riêng cho summary/mindmap/audio vs một agent endpoint có tool calling.
  - Chọn một agent endpoint vì mọi đường vào đi qua cùng vòng lặp AI, sửa prompt/hành vi một chỗ và stream được trace thống nhất.
  - Phương án bị loại: endpoint riêng cho từng tính năng vì dễ lệch hành vi và đọc lại tài liệu nhiều lần khi user yêu cầu combo.

## §9. Changelog

| Thời điểm | Đổi gì | Vì sao |
|---|---|---|
| 2026-07-31 | Tạo bản spec đầu dựa trên `codebase/README.md`, `02-guide.md`, `03-template-ai-spec.md`, `04-rubric.md`, `eval/` | Chốt mô tả prototype hiện có và đánh dấu các phần cần bổ sung evidence/validation |
| TODO | Sửa S01 để summary luôn có citation | Eval hiện fail 1/37 phép kiểm: S01 `summary_has_citation` |
| TODO | Mở rộng golden set từ 10 lên >=20 case | Rubric yêu cầu >=20 case và >=10 case từ chatlog thật |
| TODO | Bổ sung log validation >=5 người | Rubric R6 yêu cầu feedback log có tên/quote nguyên văn |
