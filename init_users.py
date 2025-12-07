"""
初始化用户数据
创建默认的老师和学生账户
"""
from api.db import SessionLocal, User
from sqlalchemy.exc import IntegrityError

def init_users():
    """初始化用户数据"""
    sess = SessionLocal()
    try:
        # 创建默认老师
        teacher = sess.query(User).filter(User.id == "teacher001").first()
        if not teacher:
            teacher = User(id="teacher001", username="张老师", role="teacher")
            sess.add(teacher)
            print("✅ 创建默认老师账户: teacher001")
        else:
            print("ℹ️  老师账户已存在: teacher001")
        
        # 创建测试学生
        student = sess.query(User).filter(User.id == "student001").first()
        if not student:
            student = User(id="student001", username="学生1", role="student")
            sess.add(student)
            print("✅ 创建测试学生账户: student001")
        else:
            print("ℹ️  学生账户已存在: student001")
        
        sess.commit()
        print("\n✅ 用户初始化完成！")
        print("\n可用账户：")
        print("  老师: teacher001 (张老师)")
        print("  学生: student001 (学生1)")
        
    except IntegrityError as e:
        sess.rollback()
        print(f"❌ 创建用户失败: {e}")
    except Exception as e:
        sess.rollback()
        print(f"❌ 错误: {e}")
    finally:
        sess.close()

if __name__ == "__main__":
    init_users()

