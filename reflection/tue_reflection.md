# Reflection cá nhân - Tuệ

## 1. Vai trò của mình trong nhóm

Trong mini hackathon này, mình tham gia chủ yếu ở phần viết spec, rà lại sản phẩm theo rubric và ghi nhận validation. Mình đọc lại `codebase/README.md` để hiểu prototype VLearn AI Study Agent đang hoạt động như thế nào, sau đó chuyển phần hiểu đó thành nội dung trong `spec.md`.

Vai trò của mình không chỉ là viết lại mô tả sản phẩm, mà còn là cố gắng làm rõ: nhóm đang giải quyết pain nào, lát cắt cụ thể là gì, AI được tự động đến mức nào, có những rủi ro nào, và nhóm đo chất lượng bằng cách nào.

## 2. Phần mình đã làm

Mình đã hỗ trợ nhóm ở các phần sau:

- Đọc `codebase/README.md` để hiểu kiến trúc và flow của prototype.
- Viết lại nội dung `spec.md` theo template của hackathon, gồm user/job, impact, thiết kế, nguyên tắc HAX/PAIR, các kiểu lỗi, trải nghiệm, kiểm thử và changelog.
- Tạo khung `validation/log.md` để nhóm ghi log người thử.
- Bổ sung các vấn đề phát hiện khi validation, đặc biệt là việc hệ thống không đọc được ảnh trong slide và mất ngữ cảnh khi người dùng prompt kỹ hơn nhiều lần về mind map.

## 3. AI đã hỗ trợ mình như thế nào

AI hỗ trợ mình nhiều nhất trong việc đọc, tổng hợp và biến thông tin rời rạc trong repo thành artifact có cấu trúc. Thay vì tự bắt đầu từ một trang trắng, mình dùng AI để đối chiếu giữa `guide.md`, template spec, rubric và README của codebase.

Tuy vậy, mình nhận ra AI chỉ có ích khi mình kiểm soát được yêu cầu. Nếu chỉ yêu cầu AI viết cho hay, kết quả rất dễ chung chung hoặc bịa thêm bằng chứng. Vì vậy, khi làm spec, mình cố gắng yêu cầu AI dựa trên file thật trong repo. Phần nào chưa có dữ liệu thật thì phải để `TODO`, không được viết như thể nhóm đã khảo sát hoặc validate đầy đủ.

AI cũng giúp mình diễn đạt các lỗi validation thành dạng rõ ràng hơn: task là gì, người dùng gặp vấn đề gì, mức nghiêm trọng ra sao và hành động tiếp theo là gì. Điều này giúp nhóm dễ đưa phần validation vào spec và slide demo hơn.

## 4. Một case fail của nhóm và bài học rút ra

Case fail mình thấy đáng chú ý nhất là hệ thống không đọc được nội dung nằm trong ảnh của slide. Trong bài giảng thật, nhiều thông tin quan trọng không chỉ nằm ở text mà còn nằm trong hình, bảng hoặc sơ đồ. Nếu agent chỉ đọc phần text extract được từ PDF, summary hoặc mind map có thể thiếu ý quan trọng, nhưng output vẫn nhìn khá mạch lạc nên người dùng khó nhận ra.

Một case fail khác là khi người dùng prompt kỹ hơn nhiều lần về mind map cũ, hệ thống có thể reset ngữ cảnh và không giữ được mạch chỉnh sửa trước đó. Agent vẫn gọi tool, nhưng chưa thật sự xử lý sâu theo yêu cầu mới của người dùng. Điều này cho thấy agent không chỉ cần có tool chạy được, mà còn cần thiết kế context và correction flow cẩn thận.

Bài học lớn nhất của mình là: với sản phẩm AI học tập, "chạy được" chưa đồng nghĩa với "dùng được". Kết quả phải có căn cứ, phải nói rõ giới hạn, và phải hỗ trợ người dùng sửa tiếp khi output chưa đúng ý. Nếu không có eval và validation, nhóm rất dễ chỉ nhìn happy path và tưởng sản phẩm đã ổn.

## 5. Nếu có thêm thời gian

Nếu có thêm thời gian, mình muốn nhóm ưu tiên:

1. Thêm OCR hoặc image understanding để đọc được slide có ảnh/sơ đồ.
2. Cải thiện việc lưu ngữ cảnh trong cùng session, nhất là khi người dùng chỉnh sửa mind map nhiều lần.
3. Mở rộng golden set từ 10 case lên ít nhất 20 case, có thêm các case từ validation thật.
4. Bổ sung thêm quote nguyên văn từ người thử để phần validation thuyết phục hơn.

Qua bài này, mình hiểu rõ hơn rằng spec không phải phần giấy tờ làm cho đủ. Spec giúp nhóm tự buộc mình phải nói rõ mình build gì, không build gì, lỗi nào nguy hiểm, và làm sao biết sản phẩm đang tốt lên thật.
