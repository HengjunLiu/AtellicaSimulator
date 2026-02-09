#!/usr/bin/env python3
"""清空数据库脚本"""

import sqlite3
import os

db_path = r'd:\ATS_SIM\AtellicaSimulator\data\atellica.db'

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 获取所有表名
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print(f'找到 {len(tables)} 个表:')
    for table in tables:
        table_name = table[0]
        # 获取表中的记录数
        cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
        count = cursor.fetchone()[0]
        print(f'  - {table_name}: {count} 条记录')
        
        # 清空表数据
        cursor.execute(f'DELETE FROM {table_name}')
        print(f'    已清空 {table_name}')
    
    conn.commit()
    conn.close()
    print('\n数据库已清空！')
else:
    print(f'数据库文件不存在: {db_path}')
