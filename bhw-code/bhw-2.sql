USE hmsys;

-- 插入科室
INSERT INTO departments (dept_name, dept_desc) VALUES ('内科', '普通内科诊疗'), ('外科', '普通外科诊疗');

-- 插入诊室
INSERT INTO consulting_rooms (dept_id, room_num) VALUES (1, '内科1诊室'), (2, '外科1诊室');

-- 插入员工（医生+行政）
INSERT INTO employees (emp_id, emp_name, position, dept_id, phone, title)
VALUES 
('Y001', '王医生', '医生', 1, '13800138001', '主任医师'),
('Y002', '李医生', '医生', 2, '13800138002', '主治医师'),
('X001', '张行政', '行政', 1, '13800138003', '行政主管');

-- 插入患者、预约、就诊、缴费（流程完整测试）
INSERT INTO patients (id_card, patient_name, gender, phone)
VALUES ('440101199001011234', '张三', '男', '13800138000');

INSERT INTO appointments (patient_name, phone, dept_id, expected_arrive)
VALUES ('张三', '13800138000', 1, '2024-01-20 09:30');

INSERT INTO medical_records (patient_id, room_id, doctor_id, appt_id)
VALUES (1, 1, 'Y001', 1);

INSERT INTO payments (record_id, total_amount, medical_insurance, self_pay, pay_method)
VALUES (1, 300.00, 150.00, 150.00, '医保');

/*
-- 触发器1：缴费后自动更新就诊记录状态为「已离院」
DELIMITER //
CREATE TRIGGER trg_payment_update_visit_status
AFTER INSERT ON payments
FOR EACH ROW
BEGIN
    UPDATE medical_records 
    SET visit_status = '已离院' 
    WHERE record_id = NEW.record_id;
END //
DELIMITER ;

-- 触发器2：删除就诊记录时，同步删除关联的缴费记录
DELIMITER //
CREATE TRIGGER trg_delete_medical_record
BEFORE DELETE ON medical_records
FOR EACH ROW
BEGIN
    DELETE FROM payments WHERE record_id = OLD.record_id;
END //
DELIMITER ;
*/