# دليل تنفيذ التكليف — Student Data Pipeline

هذا الدليل يشرح المشروع خطوة بخطوة للمبتدئ، مع ربط كل مرحلة بالملف المسؤول عنها.

## 0) الفكرة العامة

المشروع يستقبل بيانات الطالب من ثلاثة مصادر:

1. CSV: بيانات التعريف الأساسية.
2. REST API: GPA والحضور والحالة.
3. SQLite: المقررات والدرجات.

ثم ينفذ:

Extract → Validate → Clean → Integrate → Transform → Final Validation → Load

المفتاح المشترك هو `student_id`.

## 1) تجهيز البيئة

نفّذ:

```bash
pip install -r requirements.txt
```

لماذا؟
- `pandas` للتعامل مع الجداول والبيانات.
- `requests` لإرسال HTTP requests إلى REST API.
- `sqlite3` موجودة أصلًا في Python ولا تحتاج تثبيتًا.

إذا كان PyCharm لا يحتوي Interpreter، يجب ربط المشروع ببيئة Python أولًا.

## 2) تجهيز CSV

الملف:

`data/raw/students.csv`

تعمدنا وضع مشاكل مقصودة مثل:
- `Student ID` و`Student_Name` لاختبار توحيد أسماء الأعمدة.
- مسافات زائدة.
- اختلاف حالة الأحرف في المدن.
- عمر غير صالح.
- سجل مكرر.
- `student_id` مفقود.
- عمر مفقود.
- مدينة مفقودة.

الهدف هو أن يكون الاختبار واقعيًا، وليس مجرد بيانات صحيحة دائمًا.

## 3) تجهيز SQLite

نفّذ مرة واحدة:

```bash
python setup_database.py
```

ينشئ:

`database/students.db`

ويحتوي على:
- `courses`
- `enrollments`

قاعدة `enrollments` تسمح بأكثر من صف للطالب الواحد؛ لأن الطالب قد يسجل أكثر من مقرر. لذلك لا نعامل `student_id` كقيمة فريدة داخل جدول التسجيلات، بل نجمع التسجيلات لاحقًا إلى صف واحد لكل طالب.

## 4) تجهيز REST API

التكليف يسمح باستخدام Mock API محلي عند الحاجة. استخدمنا API محليًا لضمان أن المشروع يعمل دون الاعتماد على خدمة خارجية.

الملف:

`api_server.py`

يقرأ:

`data/raw/api_students.json`

ويعرض endpoint:

`http://127.0.0.1:8000/students`

شغله في Terminal منفصل:

```bash
python api_server.py
```

## 5) Extract

### CSV

`app/sources/csv_source.py`

المسؤولية الوحيدة: قراءة CSV وإعادته كـ DataFrame.

### API

`app/sources/api_source.py`

المسؤولية:
- إرسال GET request.
- التعامل مع Timeout.
- التعامل مع Connection Error.
- التعامل مع HTTP Error.
- التحقق من JSON.
- رفض الرد الفارغ.
- تحويل JSON إلى DataFrame.

### SQLite

`app/sources/database_source.py`

المسؤولية:
- الاتصال بـ SQLite.
- تنفيذ SQL JOIN بين `enrollments` و`courses`.
- إعادة البيانات كـ DataFrame.

لماذا ثلاثة ملفات؟
لأن كل مصدر له طريقة استخراج مختلفة، وفصلها يجعل التوسعة والاختبار أسهل.

## 6) Validation قبل الدمج

`app/validation/quality.py`

القواعد الأساسية:

```text
student_id != NULL
age: 16..80
gpa: 0..4
attendance: 0..100
score: 0..100
```

ويتم اكتشاف التكرار في مصادر الطلاب وفي الناتج النهائي.

ملاحظة هندسية: `enrollments` يحتوي عدة صفوف للطالب الواحد بطبيعته، لذلك شرط uniqueness لا يطبق على `student_id` داخل تفاصيل التسجيلات.

## 7) Cleaning

`app/transformation/cleaner.py`

وظائفه:

### توحيد الأعمدة

مثال:

```text
Student ID → student_id
Student_Name → student_name
```

### إزالة السجلات المخالفة

السجلات التي تفشل قاعدة صلبة لا تدخل إلى البيانات النهائية.

### معالجة Missing Values

- Missing `student_id` → رفض.
- Missing `age` → median للأعمار الصالحة في CSV.
- Missing `gpa` → median للـ GPA الصالح في API.
- Missing `attendance` → mean للحضور الصالح في API.
- Missing text → `Unknown`.
- Missing database score → رفض التسجيل لأنه لا يصلح لحساب متوسط موثوق.

### تنظيف النص

نستخدم `strip()` للمسافات و`title()` لتوحيد حالة الأحرف في الحقول النصية.

## 8) Integration

`app/transformation/integration.py`

الدمج باستخدام:

`student_id`

بيانات SQLite لها علاقة one-to-many مع الطالب، لذلك نحولها إلى مستوى الطالب:

- `course_count`
- `avg_score`

ثم نعمل inner join:

```text
CSV + API + DATABASE
```

النتيجة: صف واحد لكل طالب موجود وصالح في المصادر الثلاثة.

## 9) Transformation

`app/transformation/transformer.py`

ينفذ:
- تحويل النصوص الرقمية إلى أرقام.
- تحويل `student_id` و`age` إلى نوع رقمي مناسب.
- تقريب GPA والحضور والدرجات.
- إنشاء `performance_level`.
- إنشاء `attendance_status`.
- إضافة `source` لتتبع خط البيانات.

قواعد GPA:

```text
>= 3.5 Excellent
>= 3.0 Very Good
>= 2.5 Good
>= 2.0 Acceptable
<  2.0 At Risk
```

قواعد الحضور:

```text
>= 75 Good
<  75 Low
```

## 10) Final Validation

نفحص الناتج بعد التكامل والتحويل مرة أخرى.

هذا مهم لأن البيانات قد تبدو سليمة في المصادر منفردة، لكن عملية الدمج والتحويل قد تنتج قيمة غير متوقعة.

إذا ظهرت أخطاء هنا، تُسجل أيضًا في `rejected_records.csv`.

## 11) Load

`app/output/csv_writer.py`

المخرجات:

```text
data/processed/final_dataset.csv
data/rejected/rejected_records.csv
```

## 12) Logging

`app/utils/logger.py`

الـ Pipeline يسجل:
- بداية استخراج CSV.
- عدد سجلات CSV.
- بداية API.
- عدد سجلات API.
- بداية SQLite.
- عدد سجلات SQLite.
- مشاكل Validation.
- عدد السجلات بعد التنظيف.
- عدد سجلات الدمج.
- عدد السجلات النهائية.
- عدد المرفوض.
- التكرارات.
- مدة التنفيذ.

ويحفظها في:

`logs/pipeline.log`

## 13) تشغيل Pipeline

يجب فتح Terminalين.

### Terminal 1

```bash
python api_server.py
```

اتركه يعمل.

### Terminal 2

```bash
python main.py
```

## 14) Tests

نفّذ:

```bash
python -m unittest discover -s tests -v
```

الاختبارات الموجودة تغطي:
- CSV extraction.
- API extraction.
- SQLite extraction.
- duplicate handling.
- missing values.
- invalid records.
- integration.
- final output existence.

## 15) ما الذي يجب أن تراه بعد التشغيل؟

في النموذج المرفق تم اختبار المشروع بنجاح على بيئة Python 3.13، ومرّت الاختبارات الثمانية بنجاح.

الناتج التجريبي:

- CSV records: 12
- API records: 12
- Database records: 15
- Integrated records: 7
- Valid records: 7
- Rejected records: 9
- Duplicate records: 3
- Missing values after cleaning: 0

هذه الأرقام تخص بيانات الاختبار الموجودة داخل هذه النسخة من المشروع.

## 16) كيف تشرح المشروع للمدرب؟

يمكنك شرح كل طبقة بهذه الجملة:

- Sources: من أين جاءت البيانات؟
- Validation: هل البيانات مقبولة؟
- Cleaning: كيف أصلح القيم القابلة للإصلاح؟
- Integration: كيف أربط المصادر؟
- Transformation: كيف أجعلها صالحة للتحليل؟
- Final Validation: هل الناتج النهائي ما زال مطابقًا للقواعد؟
- Output: أين أحفظ الناتج؟
- Logging: كيف أعرف ما الذي حدث أثناء التشغيل؟

## 17) إضافات التميز

بعد إنهاء المتطلبات الأساسية يمكن إضافة:
- `config.json` لمسارات ومصادر البيانات.
- Incremental Processing.
- Data Lineage أوسع.
- Metrics أكثر تفصيلًا.
- دعم Excel أو JSON أو MySQL أو PostgreSQL دون إعادة كتابة الطبقة الأساسية.

لا تبدأ بهذه الإضافات قبل التأكد من أن المتطلبات الأساسية تعمل.
