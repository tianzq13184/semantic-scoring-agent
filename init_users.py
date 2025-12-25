"""
Initialize user data
Create default teacher and student accounts
"""
from api.db import SessionLocal, User
from sqlalchemy.exc import IntegrityError

def init_users():
    """Initialize user data"""
    sess = SessionLocal()
    try:
        teacher = sess.query(User).filter(User.id == "teacher001").first()
        if not teacher:
            teacher = User(id="teacher001", username="Teacher Zhang", role="teacher")
            sess.add(teacher)
            print("Created default teacher account: teacher001")
        else:
            print("Teacher account already exists: teacher001")
        
        student = sess.query(User).filter(User.id == "student001").first()
        if not student:
            student = User(id="student001", username="Student 1", role="student")
            sess.add(student)
            print("Created test student account: student001")
        else:
            print("Student account already exists: student001")
        
        sess.commit()
        print("\nUser initialization completed!")
        print("\nAvailable accounts:")
        print("  Teacher: teacher001 (Teacher Zhang)")
        print("  Student: student001 (Student 1)")
        
    except IntegrityError as e:
        sess.rollback()
        print(f"Failed to create user: {e}")
    except Exception as e:
        sess.rollback()
        print(f"Error: {e}")
    finally:
        sess.close()

if __name__ == "__main__":
    init_users()

