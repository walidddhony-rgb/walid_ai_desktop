هذا Hotfix يعالج مشكلتين:
1) المخرجات العربية لا تظهر في نتائج exec (كان يظهر ": 130" بدل النص الكامل).
2) التعلّم التلقائي يحفظ حقائق عامة مثل "this folder contains at least one file".

التغييرات:
- code_executor.py يضيف # -*- coding: utf-8 -*- في رأس ملف بايثون المؤقت.
- code_executor.py يضبط PYTHONIOENCODING=utf-8 و PYTHONUTF8=1 في بيئة التنفيذ.
- worker.py يطلب من النموذج استخدام print بالإنجليزية لتجنب مشاكل الترميز.
- worker.py يرفع الحد الأدنى للحقيقة إلى 20 حرفًا و5 كلمات.
- worker.py يضيف بادئات محظورة جديدة: this folder, this directory, there are, there is, الخ.

طريقة التطبيق:
1) فك الأرشيف واستبدل الملفين:
   core/code_executor.py
   agent/worker.py
2) شغّل:
   python -m py_compile core\code_executor.py
   python -m py_compile agent\worker.py
3) ثم:
   python main.py
