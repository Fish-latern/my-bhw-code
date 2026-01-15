# db_config.py
import pymysql
from pymysql.err import OperationalError, ProgrammingError

# MySQL 连接配置（根据你的本地环境修改）
DB_CONFIG = {
    "host": "localhost",
    "user": "root",       # 你的 MySQL 用户名
    "password": "candy31415926535", # 你的 MySQL 密码
    "database": "hmsys",
    "charset": "utf8mb4"
}

# 封装 SQL 执行函数（通用增删改查）
def execute_sql(sql, params=None, fetch=False):
    conn = None
    cursor = None
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(sql, params or ())
        conn.commit()
        
        if fetch:
            return {"status": "success", "data": cursor.fetchall(), "rows": 0}
        else:
            return {"status": "success", "rows": cursor.rowcount, "data": None}
    
    except (OperationalError, ProgrammingError) as e:
        if conn:
            conn.rollback()
        # 异常时也返回rows字段，避免前端报错
        return {"status": "error", "msg": str(e), "rows": 0, "data": None}
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()