# Reflection cá nhân - Hồ Trọng Hảo

## 1. Vai trò của mình trong nhóm

Trong mini hackathon này, mình tham gia chủ yếu ở phần hỗ trợ phát triển và thử nghiệm các hoạt động của hệ thống, đặc biệt là các phần liên quan đến prompt, agent behavior và trải nghiệm người dùng. Mình đọc lại các tài liệu trong repo để hiểu rõ yêu cầu của sản phẩm, sau đó đóng góp vào việc làm cho hệ thống trở nên rõ ràng hơn về luồng xử lý và cách thể hiện kết quả.

Vai trò của mình không chỉ là chạy thử prototype, mà còn cố gắng giúp nhóm nhìn rõ hơn về những điểm hệ thống đang làm tốt, nơi nào còn thiếu và cần cải thiện để phù hợp với mục tiêu của hackathon.

## 2. Phần mình đã làm

Mình đã hỗ trợ nhóm ở các phần sau:

- Tìm hiểu và phân tích các yêu cầu trong spec và rubric để hiểu rõ mục tiêu của dự án.
- Hỗ trợ kiểm tra cách prompt và agent xử lý các nhiệm vụ liên quan đến việc tóm tắt, suy luận và trả lời câu hỏi từ tài liệu học tập.
- Quan sát các case thử nghiệm và ghi nhận những tình huống hệ thống hoạt động chưa tốt hoặc chưa ổn định.
- Đóng góp vào việc làm rõ các vấn đề cần ưu tiên cải thiện trong quá trình validation và demo.

## 3. AI đã hỗ trợ mình như thế nào

AI giúp mình rất nhiều trong việc nhanh chóng hiểu cấu trúc của prototype và chuyển những hiểu biết rời rạc thành một cách nhìn hệ thống rõ ràng hơn. Thay vì phải đọc từng phần một cách thủ công và tự suy luận từ đầu, mình có thể dùng AI để đối chiếu giữa spec, README, rubric và các thử nghiệm thực tế.

Tuy nhiên, mình cũng nhận ra rằng AI chỉ thật sự hữu ích khi được dùng với yêu cầu rõ ràng và có kiểm soát. Nếu chỉ hỏi chung chung, AI dễ đưa ra câu trả lời trừu tượng hoặc không sát thực tế. Vì vậy, khi làm việc với hệ thống, mình cố gắng đặt câu hỏi cụ thể, dựa trên các tài liệu thật và các kết quả thử nghiệm thật để tránh việc “thấy có vẻ đúng” nhưng không đủ căn cứ.

AI cũng giúp mình diễn đạt các vấn đề kỹ thuật và trải nghiệm người dùng theo cách dễ hiểu hơn, đặc biệt khi cần chuyển từ lỗi thực tế sang ghi chú validation hoặc phần trình bày demo.

## 4. Một case fail của nhóm và bài học rút ra

Một case fail đáng chú ý là khi hệ thống phải xử lý các câu hỏi hoặc yêu cầu phức tạp hơn mức bình thường, nó có thể mất ngữ cảnh hoặc trả lời chưa đủ chính xác. Trong những tình huống như vậy, người dùng vẫn thấy hệ thống “có phản hồi”, nhưng phản hồi đó chưa thật sự đồng bộ với yêu cầu mới và có thể dẫn đến hiểu nhầm.

Một vấn đề khác là hệ thống vẫn còn chạm phải giới hạn khi phải làm việc với các tài liệu có nhiều thông tin hình ảnh, sơ đồ hoặc nội dung không chỉ nằm trong text thuần túy. Điều này làm giảm độ tin cậy của output dù phần trình bày có vẻ mạch lạc.

Bài học lớn nhất của mình là: với sản phẩm AI học tập, “chạy được” chưa đủ. Sản phẩm cần phải có độ tin cậy, có khả năng giữ ngữ cảnh tốt, và phải thể hiện rõ giới hạn để người dùng biết khi nào cần kiểm tra lại kết quả.

## 5. Nếu có thêm thời gian

Nếu có thêm thời gian, mình muốn nhóm ưu tiên:

1. Cải thiện khả năng giữ ngữ cảnh trong các session dài hoặc khi người dùng chỉnh sửa nhiều lần.
2. Tăng khả năng xử lý các nội dung có hình ảnh, sơ đồ và cấu trúc không chỉ là text thuần túy.
3. Mở rộng bộ test và validation với nhiều case thực tế hơn để đánh giá độ ổn định của hệ thống.
4. Bổ sung thêm bằng chứng thực tế từ người dùng để làm cho validation và demo thuyết phục hơn.

Qua bài này, mình hiểu rõ hơn rằng một sản phẩm AI không chỉ cần có chức năng hoạt động tốt, mà còn cần có cơ chế đánh giá, kiểm soát lỗi và cách trình bày giới hạn rõ ràng để người dùng thật sự tin và sử dụng được.
