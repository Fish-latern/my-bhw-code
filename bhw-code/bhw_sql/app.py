# app.py
from flask import Flask, render_template, request, jsonify
from bhw_try import execute_sql

app = Flask(__name__)

# -------------------------- 通用页面路由 --------------------------
@app.route('/')
def index():
    # 首页：角色选择
    return render_template('index.html')

# -------------------------- 患者模块（聚焦 INSERT/SELECT） --------------------------
# 1. 患者预约页面
@app.route('/patient/appointment', methods=['GET'])
def appointment_page():
    # 查询所有科室（供预约时选择）
    dept_sql = "SELECT dept_id, dept_name FROM departments"
    dept_result = execute_sql(dept_sql, fetch=True)
    return render_template('patient/appointment.html', depts=dept_result['data'])

# 2. 提交预约（执行 INSERT 语句）
@app.route('/patient/submit_appointment', methods=['POST'])
def submit_appointment():
    # 获取前端表单数据
    name = request.form.get('name')
    phone = request.form.get('phone')
    dept_id = request.form.get('dept_id')
    expected_time = request.form.get('expected_time')
    
    # 复用之前的预约 INSERT SQL（参数化防止注入）
    sql = """
    INSERT INTO appointments (patient_name, phone, dept_id, expected_arrive)
    VALUES (%s, %s, %s, %s)
    """
    params = (name, phone, dept_id, expected_time)
    result = execute_sql(sql, params)
    
    if result['status'] == 'success':
        return f"预约成功！预约ID：{result['rows']}（SQL执行成功，影响行数：{result['rows']}）"
    else:
        return f"预约失败：{result['msg']}（SQL执行出错）"

# 3. 患者查询预约记录（执行 SELECT 语句）
@app.route('/patient/query_appointment', methods=['POST'])
def query_appointment():
    phone = request.form.get('phone')
    # 复用之前的预约查询 SQL
    sql = """
    SELECT appt_id, patient_name, dept_id, expected_arrive, appt_status 
    FROM appointments WHERE phone = %s
    """
    result = execute_sql(sql, params=(phone,), fetch=True)
    return jsonify(result)

# -------------------------- 前台登记模块（预约转就诊核心） --------------------------
# 1. 前台登记页面（核验预约+登记患者）
@app.route('/reception/register', methods=['GET'])
def register_page():
    # 查询所有科室、诊室、医生（供登记时选择）
    dept_sql = "SELECT dept_id, dept_name FROM departments"
    room_sql = "SELECT room_id, room_num FROM consulting_rooms"
    doctor_sql = "SELECT emp_id, emp_name FROM employees WHERE position = '医生'"
    depts = execute_sql(dept_sql, fetch=True)['data']
    rooms = execute_sql(room_sql, fetch=True)['data']
    doctors = execute_sql(doctor_sql, fetch=True)['data']
    return render_template('reception/register.html', depts=depts, rooms=rooms, doctors=doctors)

# 2. 核验预约（根据手机号/预约ID查询预约信息，执行SELECT关联查询）
@app.route('/reception/check_appointment', methods=['POST'])
def check_appointment():
    # 支持手机号或预约ID核验
    phone = request.form.get('phone')
    appt_id = request.form.get('appt_id')
    
    # 构建查询SQL（优先按预约ID，其次按手机号）
    if appt_id:
        sql = "SELECT * FROM appointments WHERE appt_id = %s AND appt_status = '未就诊'"
        params = (appt_id,)
    elif phone:
        sql = "SELECT * FROM appointments WHERE phone = %s AND appt_status = '未就诊'"
        params = (phone,)
    else:
        return jsonify({"status": "error", "msg": "请输入手机号或预约ID"})
    
    result = execute_sql(sql, params=params, fetch=True)
    return jsonify(result)

# 3. 提交登记（核心：串联INSERT/UPDATE SQL）
# 修复后的submit_register路由
@app.route('/reception/submit_register', methods=['POST'])
def submit_register():
    # 初始化变量，避免未定义
    patient_insert = {"rows": 0, "status": "success"}  # 默认值
    try:
        # 1. 获取前端提交的登记数据
        appt_id = request.form.get('appt_id')
        id_card = request.form.get('id_card')
        patient_name = request.form.get('patient_name')
        gender = request.form.get('gender')
        phone = request.form.get('phone')
        room_id = request.form.get('room_id')
        doctor_id = request.form.get('doctor_id')

        # 步骤1：检查患者是否已存在
        check_patient_sql = "SELECT patient_id FROM patients WHERE id_card = %s"
        patient_result = execute_sql(check_patient_sql, params=(id_card,), fetch=True)
        if patient_result['status'] != 'success':
            return f"查询患者失败：{patient_result['msg']}"

        # 步骤2：新增患者（若不存在）
        patient_id = None
        if not patient_result['data']:
            insert_patient_sql = """
            INSERT INTO patients (id_card, patient_name, gender, phone)
            VALUES (%s, %s, %s, %s)
            """
            patient_params = (id_card, patient_name, gender, phone)
            patient_insert = execute_sql(insert_patient_sql, patient_params)
            if patient_insert['status'] != 'success':
                return f"新增患者失败：{patient_insert['msg']}"
            # 更安全的获取新增ID方式（使用INSERT的返回值，而非LAST_INSERT_ID）
            # 补充：execute_sql的增删改返回rows=新增行数，同时查询该身份证的患者ID
            patient_id = execute_sql(check_patient_sql, params=(id_card,), fetch=True)['data'][0]['patient_id']
        else:
            # 患者已存在，复用ID
            patient_id = patient_result['data'][0]['patient_id']

        # 步骤3：生成就诊记录
        insert_medical_sql = """
        INSERT INTO medical_records (patient_id, room_id, doctor_id, appt_id, visit_status)
        VALUES (%s, %s, %s, %s, '就诊中')
        """
        medical_params = (patient_id, room_id, doctor_id, appt_id)
        medical_insert = execute_sql(insert_medical_sql, medical_params)
        if medical_insert['status'] != 'success':
            return f"生成就诊记录失败：{medical_insert['msg']}"
        record_id = medical_insert['rows']

        # 步骤4：更新预约状态
        update_appt_sql = "UPDATE appointments SET appt_status = '已就诊' WHERE appt_id = %s"
        update_appt = execute_sql(update_appt_sql, params=(appt_id,))
        if update_appt['status'] != 'success':
            # 仅提示警告，不中断流程（就诊记录已生成）
            warn_msg = f"⚠️ 预约状态更新失败：{update_appt['msg']}<br>"
        else:
            warn_msg = ""

        # 正常返回，此时patient_insert必有定义
        return f"""
        登记成功！<br>
        {warn_msg}
        患者ID：{patient_id}<br>
        就诊记录ID：{record_id}<br>
        （新增患者SQL影响行数：{patient_insert['rows']}，生成就诊记录SQL影响行数：{medical_insert['rows']}，更新预约状态SQL影响行数：{update_appt.get('rows', 0)}）
        """

    except Exception as e:
        # 捕获所有Python异常，返回友好提示
        return f"登记流程异常：{str(e)}<br>注意：部分数据可能已写入数据库，请核对！"

# 4. 就诊确认（可选：更新就诊状态为“就诊中/已接诊”，仅演示SQL UPDATE）
@app.route('/reception/confirm_visit', methods=['POST'])
def confirm_visit():
    record_id = request.form.get('record_id')
    status = request.form.get('status', '就诊中')  # 默认为就诊中，可改为“已接诊”
    
    update_sql = "UPDATE medical_records SET visit_status = %s WHERE record_id = %s"
    result = execute_sql(update_sql, params=(status, record_id))
    
    if result['status'] == 'success':
        return f"就诊状态更新成功！（SQL影响行数：{result['rows']}）"
    else:
        return f"更新失败：{result['msg']}"
# -------------------------- 前台模块（聚焦 INSERT/UPDATE/SELECT） --------------------------
# 1. 缴费页面
@app.route('/reception/payment', methods=['GET'])
def payment_page():
    return render_template('reception/payment.html')

# 2. 提交缴费（执行 INSERT + UPDATE 事务，复用之前的缴费 SQL）
@app.route('/reception/submit_payment', methods=['POST'])
def submit_payment():
    record_id = request.form.get('record_id')
    total = request.form.get('total')
    insurance = request.form.get('insurance')
    self_pay = request.form.get('self_pay')
    method = request.form.get('method')
    
    # 步骤1：插入缴费记录（INSERT）
    pay_sql = """
    INSERT INTO payments (record_id, total_amount, medical_insurance, self_pay, pay_method)
    VALUES (%s, %s, %s, %s, %s)
    """
    pay_params = (record_id, total, insurance, self_pay, method)
    pay_result = execute_sql(pay_sql, pay_params)
    
    if pay_result['status'] != 'success':
        return f"缴费失败：{pay_result['msg']}"
    
    # 步骤2：更新就诊状态（UPDATE）
    update_sql = """
    UPDATE medical_records SET visit_status = '已离院' WHERE record_id = %s
    """
    update_result = execute_sql(update_sql, params=(record_id,))
    
    if update_result['status'] == 'success':
        return f"缴费成功！（缴费SQL影响行数：{pay_result['rows']}，更新状态SQL影响行数：{update_result['rows']}）"
    else:
        return f"缴费记录插入成功，但更新就诊状态失败：{update_result['msg']}"

# 3. 前台查询收费报表（执行 GROUP BY 统计 SQL）
@app.route('/reception/report', methods=['POST'])
def get_report():
    date = request.form.get('date')
    # 复用之前的收费统计 SQL
    sql = """
    SELECT 
        DATE(pay_time) AS pay_date,
        SUM(total_amount) AS total_income,
        SUM(medical_insurance) AS insurance_income,
        SUM(self_pay) AS self_pay_income,
        COUNT(DISTINCT record_id) AS visit_count
    FROM payments 
    WHERE DATE(pay_time) = %s
    GROUP BY DATE(pay_time)  -- 补充这一行，匹配SELECT里的非聚合列
    """
    result = execute_sql(sql, params=(date,), fetch=True)
    return jsonify(result)

# -------------------------- 管理员模块（聚焦 INSERT/SELECT/GROUP BY） --------------------------
# 1. 排班管理页面
@app.route('/admin/schedule', methods=['GET'])
def schedule_page():
    # 查询医生和诊室列表（供排班选择）
    doctor_sql = "SELECT emp_id, emp_name FROM employees WHERE position = '医生'"
    room_sql = "SELECT room_id, room_num FROM consulting_rooms"
    doctors = execute_sql(doctor_sql, fetch=True)['data']
    rooms = execute_sql(room_sql, fetch=True)['data']
    return render_template('admin/schedule.html', doctors=doctors, rooms=rooms)

# 2. 提交排班（执行 INSERT 语句）
@app.route('/admin/submit_schedule', methods=['POST'])
def submit_schedule():
    doctor_id = request.form.get('doctor_id')
    room_id = request.form.get('room_id')
    date = request.form.get('date')
    start = request.form.get('start')
    end = request.form.get('end')
    
    # 复用之前的排班 INSERT SQL
    sql = """
    INSERT INTO schedules (doctor_id, room_id, schedule_date, start_time, end_time)
    VALUES (%s, %s, %s, %s, %s)
    """
    params = (doctor_id, room_id, date, start, end)
    result = execute_sql(sql, params)
    
    if result['status'] == 'success':
        return f"排班成功！（SQL执行成功，影响行数：{result['rows']}）"
    else:
        return f"排班失败：{result['msg']}（SQL执行出错）"

# 启动服务
if __name__ == '__main__':
    app.run(debug=True, port=5000)  # 调试模式，端口5000