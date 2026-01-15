CREATE DATABASE IF NOT EXISTS HMSYS CHARACTER SET utf8mb4;
USE HMSYS;
-- 1. 科室表（存储科室信息）
CREATE TABLE departments (
    dept_id INT PRIMARY KEY AUTO_INCREMENT,  -- 科室ID（主键）
    dept_name VARCHAR(50) NOT NULL UNIQUE,   -- 科室名称（唯一，如内科、外科）
    dept_desc VARCHAR(200) DEFAULT ''        -- 科室描述
);

-- 2. 诊室表（存储诊室信息）
CREATE TABLE consulting_rooms (
    room_id INT PRIMARY KEY AUTO_INCREMENT,  -- 诊室ID（主键）
    dept_id INT NOT NULL,                    -- 所属科室（外键）
    room_num VARCHAR(20) NOT NULL UNIQUE,    -- 诊室编号（如内科1诊室）
    status ENUM('可用','维修') DEFAULT '可用',-- 诊室状态
    FOREIGN KEY (dept_id) REFERENCES departments(dept_id)
);

-- 3. 员工表（含医生、护士、行政人员，工号唯一）
CREATE TABLE employees (
    emp_id VARCHAR(20) PRIMARY KEY,          -- 工号（主键，如Y001）
    emp_name VARCHAR(50) NOT NULL,           -- 姓名
    position ENUM('医生','护士','行政') NOT NULL,-- 岗位
    dept_id INT NOT NULL,                    -- 所属科室（外键）
    phone VARCHAR(20) NOT NULL,              -- 联系方式
    work_status ENUM('在岗','休假','离职') DEFAULT '在岗',-- 工作状态
    schedule_auth BOOLEAN DEFAULT TRUE,      -- 排班权限（仅医生需要）
    title VARCHAR(50) DEFAULT '',            -- 职称（如主任医师、护士）
    FOREIGN KEY (dept_id) REFERENCES departments(dept_id)
);

-- 4. 患者表（身份证号唯一，存储患者核心信息）
CREATE TABLE patients (
    patient_id INT PRIMARY KEY AUTO_INCREMENT,-- 患者ID（主键）
    id_card VARCHAR(18) NOT NULL UNIQUE,     -- 身份证号（唯一，核心标识）
    patient_name VARCHAR(50) NOT NULL,       -- 姓名
    gender ENUM('男','女','其他') NOT NULL,   -- 性别
    phone VARCHAR(20) NOT NULL,              -- 联系电话
    register_time DATETIME DEFAULT CURRENT_TIMESTAMP-- 首次登记时间
);

-- 5. 预约表（存储患者预约信息，关联患者和科室）
CREATE TABLE appointments (
    appt_id INT PRIMARY KEY AUTO_INCREMENT,  -- 预约ID（主键）
    patient_id INT,                          -- 患者ID（外键，未注册患者可为NULL）
    patient_name VARCHAR(50) NOT NULL,       -- 预约人姓名（兼容未注册患者）
    phone VARCHAR(20) NOT NULL,              -- 预约人电话
    dept_id INT NOT NULL,                    -- 预约科室（外键）
    expected_arrive DATETIME NOT NULL,       -- 预计到达时间
    appt_status ENUM('未就诊','已就诊','已取消') DEFAULT '未就诊',-- 预约状态
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,-- 预约创建时间
    FOREIGN KEY (dept_id) REFERENCES departments(dept_id)
);

-- 6. 就诊记录表（核心表，关联患者、诊室、医生）
CREATE TABLE medical_records (
    record_id INT PRIMARY KEY AUTO_INCREMENT,-- 就诊记录ID（主键）
    patient_id INT NOT NULL,                 -- 患者ID（外键）
    room_id INT NOT NULL,                    -- 就诊诊室（外键）
    doctor_id VARCHAR(20) NOT NULL,          -- 接诊医生（外键，关联员工表）
    visit_time DATETIME DEFAULT CURRENT_TIMESTAMP,-- 就诊时间
    visit_status ENUM('就诊中','已离院','未缴费') DEFAULT '就诊中',-- 就诊状态
    appt_id INT NULL,                        -- 关联预约ID（如为预约患者）
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    FOREIGN KEY (room_id) REFERENCES consulting_rooms(room_id),
    FOREIGN KEY (doctor_id) REFERENCES employees(emp_id)
);

-- 7. 缴费表（关联就诊记录，存储缴费详情）
CREATE TABLE payments (
    pay_id INT PRIMARY KEY AUTO_INCREMENT,   -- 缴费ID（主键）
    record_id INT NOT NULL UNIQUE,           -- 关联就诊记录（1对1，唯一）
    total_amount DECIMAL(10,2) NOT NULL CHECK (total_amount >= 0),-- 总费用（非负）
    medical_insurance DECIMAL(10,2) NOT NULL CHECK (medical_insurance >= 0),-- 医保金额
    self_pay DECIMAL(10,2) NOT NULL CHECK (self_pay >= 0),-- 自费金额
    pay_time DATETIME DEFAULT CURRENT_TIMESTAMP,-- 缴费时间
    pay_method ENUM('现金','微信','支付宝','医保') NOT NULL,-- 缴费方式
    FOREIGN KEY (record_id) REFERENCES medical_records(record_id)
);

-- 8. 排班表（关联医生和诊室，存储排班信息）
CREATE TABLE schedules (
    schedule_id INT PRIMARY KEY AUTO_INCREMENT,-- 排班ID（主键）
    doctor_id VARCHAR(20) NOT NULL,          -- 医生工号（外键）
    room_id INT NOT NULL,                    -- 诊室ID（外键）
    schedule_date DATE NOT NULL,             -- 排班日期
    start_time TIME NOT NULL,                -- 接诊开始时间
    end_time TIME NOT NULL,                  -- 接诊结束时间
    status ENUM('有效','取消') DEFAULT '有效',-- 排班状态
    FOREIGN KEY (doctor_id) REFERENCES employees(emp_id),
    FOREIGN KEY (room_id) REFERENCES consulting_rooms(room_id),
    UNIQUE KEY unique_schedule (doctor_id, schedule_date, start_time)-- 避免医生同一时间重复排班
);

-- 索引设计（提升查询效率）
CREATE INDEX idx_patients_idcard ON patients(id_card);-- 患者身份证号查询索引
CREATE INDEX idx_patients_phone ON patients(phone);-- 患者电话查询索引
CREATE INDEX idx_medical_records_patient ON medical_records(patient_id);-- 患者就诊记录查询
CREATE INDEX idx_medical_records_time ON medical_records(visit_time);-- 按时间统计就诊人次
CREATE INDEX idx_payments_time ON payments(pay_time);-- 按时间统计缴费
CREATE INDEX idx_schedules_doctor ON schedules(doctor_id);-- 医生排班查询
CREATE INDEX idx_appointments_phone ON appointments(phone);-- 预约核验（电话）