#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据导入脚本
从 shared/ozon-data/ 导入历史数据到数据库
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from ecom_v51.database.models import (
    Base, DimShop, DimPlatform, FactSkuDaily, ImportBatch
)
from ecom_v51.config.settings import settings


class DataImporter:
    """数据导入器"""
    
    def __init__(self):
        # 初始化数据库
        self.engine = create_engine(settings.DATABASE_URL, echo=False)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        print(f"✅ 数据库连接成功: {settings.DATABASE_URL[:30]}...")
    
    def init_dimensions(self):
        """初始化维度表"""
        print("\n📊 初始化维度表...")
        
        # 平台
        platform = DimPlatform(
            code='ozon',
            name='Ozon',
            description='Ozon电商平台'
        )
        self.session.add(platform)
        self.session.commit()
        
        # 店铺
        shops = [
            {'code': 'YunElite', 'name': 'YunElite', 'client_id': '3055895'},
            {'code': 'ALORA', 'name': 'ALORA', 'client_id': '3328779'},
            {'code': 'YunYi', 'name': 'YunYi', 'client_id': '4022219'},
        ]
        
        for shop_data in shops:
            shop = DimShop(
                shop_code=shop_data['code'],
                shop_name=shop_data['name'],
                client_id=shop_data['client_id'],
                platform_id=platform.id,
                is_active=True
            )
            self.session.add(shop)
        
        self.session.commit()
        print(f"✅ 已创建 {len(shops)} 个店铺")
    
    def import_latest_data(self):
        """导入最新数据"""
        print("\n📥 导入最新数据...")
        
        # 读取 latest.json
        data_dir = Path(r'C:\Users\Xx1yy\.openclaw\shared\ozon-data\processed')
        latest_file = data_dir / 'latest.json'
        
        if not latest_file.exists():
            print(f"❌ 数据文件不存在: {latest_file}")
            return
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            latest_data = json.load(f)
        
        print(f"📄 读取数据: {latest_file}")
        print(f"   批次时间: {latest_data.get('batch_time')}")
        
        # 导入每个店铺的数据
        shops_data = latest_data.get('shops', {})
        
        for shop_name, shop_info in shops_data.items():
            print(f"\n🏪 导入店铺: {shop_name}")
            print(f"   产品数: {shop_info.get('total_products', 0)}")
            print(f"   订单数: {shop_info.get('fbs_orders_7d', 0)}")
            
            # 创建导入批次记录
            batch = ImportBatch(
                batch_id=f"api_{shop_name}_{latest_data.get('date', 'unknown')}_{latest_data.get('time', '000000')}",
                file_name=f"api_fetch_{shop_name}.json",
                platform='ozon',
                total_rows=shop_info.get('total_products', 0),
                status='success',
                created_at=datetime.utcnow()
            )
            
            # 查找店铺ID
            shop = self.session.query(DimShop).filter_by(shop_code=shop_name).first()
            if shop:
                batch.shop_id = shop.id
            
            self.session.add(batch)
        
        self.session.commit()
        print(f"\n✅ 数据导入完成")
    
    def import_from_raw(self, days_back=7):
        """从原始JSON导入历史数据"""
        print(f"\n📥 导入最近 {days_back} 天的历史数据...")
        
        data_dir = Path(r'C:\Users\Xx1yy\.openclaw\shared\ozon-data\raw')
        
        if not data_dir.exists():
            print(f"❌ 数据目录不存在: {data_dir}")
            return
        
        # 找到最近的日期目录
        date_dirs = sorted([d for d in data_dir.iterdir() if d.is_dir()], reverse=True)
        
        if not date_dirs:
            print("❌ 未找到数据目录")
            return
        
        # 导入最近N天的数据
        for date_dir in date_dirs[:days_back]:
            print(f"\n📅 处理日期: {date_dir.name}")
            
            # 查找该日期的所有JSON文件
            json_files = list(date_dir.glob('*.json'))
            
            for json_file in json_files:
                shop_name = json_file.stem.split('_')[0]
                print(f"   📄 {json_file.name} ({shop_name})")
                
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # TODO: 解析数据并保存到 fact_sku_daily
                    # 当前只是统计
                    
                except Exception as e:
                    print(f"   ⚠️  读取失败: {e}")
        
        print(f"\n✅ 历史数据导入完成")
    
    def show_summary(self):
        """显示数据摘要"""
        print("\n" + "="*60)
        print("📊 数据库摘要")
        print("="*60)
        
        # 统计各表记录数
        shops_count = self.session.query(DimShop).count()
        products_count = self.session.query(FactSkuDaily).count()
        batches_count = self.session.query(ImportBatch).count()
        
        print(f"店铺数: {shops_count}")
        print(f"产品记录数: {products_count}")
        print(f"导入批次数: {batches_count}")
        print("="*60 + "\n")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("V5.1 数据导入工具")
    print("="*60)
    
    importer = DataImporter()
    
    # 1. 初始化维度表
    importer.init_dimensions()
    
    # 2. 导入最新数据
    importer.import_latest_data()
    
    # 3. 导入历史数据（可选）
    # importer.import_from_raw(days_back=7)
    
    # 4. 显示摘要
    importer.show_summary()
    
    print("✅ 全部完成！\n")


if __name__ == '__main__':
    main()
