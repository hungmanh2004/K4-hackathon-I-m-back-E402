# Validation Log

## Cách dùng

- Mỗi người thử một dòng.
- Ghi đúng quote nguyên văn.
- Không viết lại cho đẹp hơn lời họ nói.
- Sau mỗi buổi test, thêm 1-2 dòng tổng hợp thay đổi đã làm hoặc lý do giữ nguyên.

## Log người dùng

| Ngày | Người thử | Vai trò | Task | Quan sát | Quote nguyên văn | Mức nghiêm trọng | Hành động tiếp theo |
|---|---|---|---|---|---|---|---|
| 2026-07-31 | Lê Văn Vương | người thử | Dùng prototype để tạo mind map từ slide có hình/ảnh | Không đọc được nội dung trong ảnh trên slide, nên mind map thiếu ý quan trọng hoặc không đúng ngữ cảnh | "Không đọc được ảnh từ slides" | cao | Cần thêm bước OCR / image understanding hoặc báo rõ giới hạn khi slide có ảnh |
| 2026-07-31 | Nguyễn Văn Long | Người dùng | Hỏi lại cùng một yêu cầu mind map sau khi prompt kỹ hơn 3 lần | Agent reset ngữ cảnh, không giữ được mạch trước đó; chỉ gọi tool cơ học, không xử lý sâu theo yêu cầu mới | "Không lưu được ngữ cảnh, ko làm mind map kĩ hơn" | cao | Cần kiểm tra lại memory trong cùng session, hoặc lưu context tóm tắt trước khi loop tiếp |
| 2026-07-31 | Trần Văn Khôi | Người dùng | Dùng prototype để tạo mind map từ slide có hình/ảnh | Không đọc được nội dung trong ảnh trên slide, nên phần tóm tắt từ slide bị hụt ý | "Thiếu nội dung từ ảnh" | cao | Bổ sung OCR hoặc báo rõ không hỗ trợ slide nhiều ảnh |
| 2026-07-31 | Nguyễn Văn Hoàng | Người dùng | Hỏi lại mind map sau khi đã nhắc kỹ nhiều lần | Agent vẫn quay lại gọi tool, không bám vào ngữ cảnh trước đó | "Sao lại gọi tool" | cao | Giảm tình trạng reset bằng cách giữ tóm tắt ngữ cảnh giữa các lượt |
| 2026-07-31 | Nguyễn Thị Vy | Người dùng | Yêu cầu làm lại mind map với cùng nội dung nhưng thêm chi tiết | Không giữ được chi tiết của lượt trước, phản hồi còn hời hợt | "Không cải thiện qua các lần gọi" | trung bình | Cần kiểm tra context handoff giữa prompt và tool loop |

## Tổng hợp sau vòng test

- Chủ đề lặp lại nhiều nhất: không đọc được ảnh trong slide; mất ngữ cảnh khi hỏi lại nhiều lần.
- Thay đổi đã làm: giữ context trong đoạn chat
- Giữ nguyên vì: không đủ thời gian để thêm OCR đọc ảnh 
- Việc đưa vào backlog: thêm OCR/image understanding cho slide có ảnh; kiểm tra lại cơ chế giữ context giữa các lượt prompt.
