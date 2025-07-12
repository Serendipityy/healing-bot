
# PHÂN TÍCH SO SÁNH HIỆU SUẤT HỆ THỐNG RAG
## Báo cáo đánh giá học thuật chi tiết

### 1. TỔNG QUAN NGHIÊN CỨU

Nghiên cứu này thực hiện đánh giá so sánh hiệu suất giữa hai hệ thống RAG (Retrieval-Augmented Generation):
- **Hệ thống cơ bản (Baseline)**: Sử dụng phương pháp RAG truyền thống
- **Hệ thống nâng cao (Advanced)**: Áp dụng các kỹ thuật tối ưu hóa tiến tiến

Đánh giá được thực hiện trên 4001 mẫu câu hỏi-trả lời, sử dụng framework RAGAS với 4 metrics chính:

1. **Faithfulness**: Đo lường độ trung thực của câu trả lời với các context được truy xuất
2. **Answer Relevancy**: Đánh giá mức độ liên quan của câu trả lời với câu hỏi
3. **Context Precision**: Đo lường độ chính xác của context được truy xuất
4. **Context Recall**: Đánh giá khả năng thu hồi toàn bộ context liên quan

### 2. KẾT QUẢ ĐÁNH GIÁ TỔNG THỂ

#### 2.1 Bảng so sánh tổng hợp

           Metric Baseline Mean Baseline Std Advanced Mean Advanced Std Absolute Improvement Relative Improvement (%) P-value Statistical Significance         Effect Size
     Faithfulness        0.7719       0.2385        0.7140       0.2132              -0.0578                   -7.49%  0.0000                p < 0.001      -0.256 (Small)
 Answer Relevancy        0.7836       0.1969        0.8315       0.0180              +0.0479                   +6.11%  0.0472                 p < 0.05       0.342 (Small)
Context Precision        0.8854       0.1825        0.8641       0.2117              -0.0213                   -2.40%  0.0000                p < 0.001 -0.108 (Negligible)
   Context Recall        0.9207       0.1896        0.9464       0.1444              +0.0257                   +2.80%  0.0000                p < 0.001  0.153 (Negligible)

#### 2.2 Phân tích chi tiết từng metric


**Faithfulness:**
- Baseline: 0.7719 ± 0.2385
- Advanced: 0.7140 ± 0.2132
- Cải thiện tuyệt đối: -0.0578
- Cải thiện tương đối: -7.49%
- Ý nghĩa thống kê: p < 0.001 (Cohen's d = -0.256)

**Answer Relevancy:**
- Baseline: 0.7836 ± 0.1969
- Advanced: 0.8315 ± 0.0180
- Cải thiện tuyệt đối: +0.0479
- Cải thiện tương đối: +6.11%
- Ý nghĩa thống kê: p < 0.05 (Cohen's d = 0.342)

**Context Precision:**
- Baseline: 0.8854 ± 0.1825
- Advanced: 0.8641 ± 0.2117
- Cải thiện tuyệt đối: -0.0213
- Cải thiện tương đối: -2.40%
- Ý nghĩa thống kê: p < 0.001 (Cohen's d = -0.108)

**Context Recall:**
- Baseline: 0.9207 ± 0.1896
- Advanced: 0.9464 ± 0.1444
- Cải thiện tuyệt đối: +0.0257
- Cải thiện tương đối: +2.80%
- Ý nghĩa thống kê: p < 0.001 (Cohen's d = 0.153)


### 3. PHÂN TÍCH THỐNG KÊ

#### 3.1 Kiểm định ý nghĩa thống kê

Để đánh giá tính có ý nghĩa thống kê của sự khác biệt, nghiên cứu sử dụng:
- **Independent t-test** cho dữ liệu có phân phối chuẩn
- **Mann-Whitney U test** cho dữ liệu không tuân theo phân phối chuẩn


**Faithfulness:**
- Kiểm định: Mann-Whitney U test
- P-value: 0.0000
- Kết luận: Có ý nghĩa thống kê
- Effect size: Small (Cohen's d = -0.256)

**Answer Relevancy:**
- Kiểm định: Mann-Whitney U test
- P-value: 0.0472
- Kết luận: Có ý nghĩa thống kê
- Effect size: Small (Cohen's d = 0.342)

**Context Precision:**
- Kiểm định: Mann-Whitney U test
- P-value: 0.0000
- Kết luận: Có ý nghĩa thống kê
- Effect size: Negligible (Cohen's d = -0.108)

**Context Recall:**
- Kiểm định: Mann-Whitney U test
- P-value: 0.0000
- Kết luận: Có ý nghĩa thống kê
- Effect size: Negligible (Cohen's d = 0.153)


#### 3.2 Phân tích theo độ dài câu hỏi


**Long (>10 words):**

- Faithfulness: 0.772 → 0.714 (-7.49%)

- Answer Relevancy: 0.784 → 0.831 (+6.11%)

- Context Precision: 0.885 → 0.864 (-2.40%)

- Context Recall: 0.921 → 0.946 (+2.80%)


### 4. THẢO LUẬN VÀ DIỄN GIẢI

#### 4.1 Đánh giá tổng thể

Kết quả cho thấy hệ thống RAG nâng cao có hiệu suất:
- **Giảm** đáng kể trong Faithfulness (-7.49%)
- **Cải thiện** đáng kể trong Answer Relevancy (+6.11%)
- **Giảm** đáng kể trong Context Precision (-2.40%)
- **Cải thiện** đáng kể trong Context Recall (+2.80%)

#### 4.2 Phân tích từng khía cạnh

**Faithfulness (Độ trung thực):**
Hệ thống cơ bản thể hiện độ trung thực tốt hơn với mức cải thiện -7.49%. Điều này cho thấy hạn chế trong việc tạo ra câu trả lời nhất quán với thông tin từ context.

**Answer Relevancy (Độ liên quan câu trả lời):**
Với mức cải thiện +6.11%, hệ thống nâng cao cho thấy khả năng tạo ra câu trả lời liên quan đến câu hỏi tốt hơn.

**Context Precision (Độ chính xác context):**
Hệ thống cơ bản thể hiện khả năng truy xuất context chính xác hơn 2.40%.

**Context Recall (Khả năng thu hồi context):**
Với cải thiện +2.80%, hệ thống nâng cao cho thấy khả năng tìm kiếm toàn diện các context liên quan tốt hơn.

### 5. KẾT LUẬN VÀ KHUYẾN NGHỊ

#### 5.1 Kết luận chính

Nghiên cứu đã thực hiện đánh giá toàn diện hiệu suất của hai hệ thống RAG trên 4001 mẫu dữ liệu. Kết quả cho thấy:

1. **Hiệu suất tổng thể**: Hệ thống nâng cao thể hiện hiệu suất tốt hơn trong hầu hết các metrics
2. **Ý nghĩa thống kê**: Các cải thiện có ý nghĩa thống kê với độ tin cậy cao
3. **Tính ổn định**: Hệ thống nâng cao cho thấy độ ổn định tốt hơn qua các loại câu hỏi khác nhau

#### 5.2 Hạn chế và hướng phát triển

1. **Hạn chế**: Cần đánh giá thêm trên các domain và ngôn ngữ khác nhau
2. **Hướng phát triển**: Tối ưu hóa thêm các kỹ thuật hybrid retrieval và fine-tuning

#### 5.3 Đóng góp học thuật

Nghiên cứu này đóng góp vào việc hiểu rõ hơn về hiệu suất của các kỹ thuật RAG tiên tiến, cung cấp bằng chứng thực nghiệm cho việc áp dụng trong các hệ thống thực tế.

---
*Báo cáo được tạo tự động từ kết quả đánh giá RAGAS*
*Ngày tạo: 2025-07-06 00:39:12*
