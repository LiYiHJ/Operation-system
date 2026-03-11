from __future__ import annotations

from .models import ImportBatchDiagnosis
from .intelligent_field_mapper import IntelligentFieldMapper

HEADER_KEYWORDS = {
    "sku": ["sku", "артикул", "seller_sku", "offer_id"],
    "impressions": ["показы", "impressions", "展示"],
    "orders": ["заказ", "orders", "订单"],
    "revenue": ["revenue", "金额", "сумм"],
}

KEY_CANDIDATES = ["sku", "артикул", "seller_sku", "offer_id"]


class ImportDiagnoser:
    """导入诊断器 - 增强版（集成智能映射器）"""
    
    def __init__(self):
        self.intelligent_mapper = IntelligentFieldMapper()  # 🆕 使用智能映射器
    
    def detect_platform(self, headers: list[str], file_name: str) -> str:
        """检测平台"""
        lowered = " ".join(headers).lower() + " " + file_name.lower()
        if any(x in lowered for x in ["ozon", "артикул", "показы"]):
            return "ozon"
        return "unknown"

    def locate_header_row(self, preview_rows: list[list[str]]) -> int | None:
        """定位表头行"""
        best_row = None
        best_score = -1
        for i, row in enumerate(preview_rows[:20]):
            text = " ".join(map(str, row)).lower()
            score = sum(1 for aliases in HEADER_KEYWORDS.values() if any(a in text for a in aliases))
            if score > best_score:
                best_score = score
                best_row = i
        return best_row if best_score > 0 else None

    def detect_key_field(self, headers: list[str]) -> str | None:
        """
        检测主键字段（使用智能映射器）
        
        🆕 改进：使用智能映射器进行字段识别，提高准确率
        """
        # 优先使用智能映射器
        for header in headers:
            standard_name, confidence, reasons = self.intelligent_mapper.detect_field(header)
            if standard_name == "sku" and confidence >= 0.7:  # ✅ 使用智能映射器，置信度阈值 0.7
                return header
        
        # 降级：使用静态候选列表
        lowered = [h.lower() for h in headers]
        for cand in KEY_CANDIDATES:
            if cand in lowered:
                return headers[lowered.index(cand)]
        
        return None

    def diagnose(
        self,
        *,
        file_name: str,
        preview_rows: list[list[str]],
        headers: list[str],
        mapped_fields: int,
        unmapped_fields: list[str],
        row_error_count: int,
    ) -> ImportBatchDiagnosis:
        """
        诊断导入问题（增强版）
        
        🆕 改进：
        - 使用智能映射器进行字段识别
        - 生成更详细的诊断报告
        - 提供更精准的建议
        """
        platform = self.detect_platform(headers, file_name)
        header_row = self.locate_header_row(preview_rows)
        key_field = self.detect_key_field(headers)  # ✅ 使用增强后的检测方法

        suggestions: list[str] = []
        
        # 表头诊断
        if header_row is None:
            suggestions.append("❌ 未检测到表头，请手动指定前20行中的真实表头行")
        else:
            suggestions.append(f"✅ 检测到表头在第 {header_row + 1} 行")
        
        # 主键诊断
        if key_field is None:
            suggestions.append("❌ 未检测到SKU主键，请映射 sku/Артикул/seller_sku/offer_id")
        else:
            suggestions.append(f"✅ 检测到主键字段: {key_field}")
        
        # 未映射字段诊断
        if unmapped_fields:
            suggestions.append(f"⚠️  存在 {len(unmapped_fields)} 个未识别字段，请在映射确认页手动绑定")
        
        # 数据错误诊断
        if row_error_count > 0:
            suggestions.append(f"⚠️  发现 {row_error_count} 行数据错误，请检查数据格式")

        # 判断状态
        status = "success"
        if header_row is None or key_field is None:
            status = "failed"
        elif row_error_count > 0 or unmapped_fields:
            status = "partial"

        return ImportBatchDiagnosis(
            file_name=file_name,
            detected_header_row=header_row,
            platform=platform,
            mapped_fields=mapped_fields,
            unmapped_fields=unmapped_fields,
            key_field=key_field,
            row_error_count=row_error_count,
            status=status,
            suggestions=suggestions,
        )
