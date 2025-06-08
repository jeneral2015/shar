import pandas as pd
import os
from datetime import datetime

def export_to_excel(self, df, filename):
    """تصدير DataFrame إلى ملف Excel"""
    try:
        # إنشاء مجلد reports إذا لم يكن موجودًا
        os.makedirs("reports", exist_ok=True)
        
        # تحديد مسار الحفظ داخل مجلد reports
        output_path = os.path.join("reports", f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        
        # تصدير DataFrame إلى ملف Excel
        df.to_excel(output_path, index=False)
        self.show_snackbar(f"تم تصدير التقرير إلى {output_path}")
    except Exception as e:
        self.show_snackbar(f"خطأ أثناء تصدير الملف: {str(e)}")
