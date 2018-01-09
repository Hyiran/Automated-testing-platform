# -*- coding: utf-8 -*-
from apps.testservice import models as mysql_db
from apps.action.views import asrtest as asrtest
from apps.action.views import nlutest as nlutest
from apps.action.views import nlptest as nlptest
from django.shortcuts import redirect
import send_email
import super_butt
import MySQLdb
import public_methods
import ConfigParser
import os
import time
shun_test_id = ""


def super_around(message):
    logger, fh, ch = public_methods.set_logger()
    try:
        table_name = message["tableName"]
        case_id = message["caseId"]
        times = int(message["times"])
        mail_valid = message["mail_valid"]
        # sheet_name = message["sheet_name"]
        # 创建test_id
        try:
            test_id = mysql_db.TestFrame.objects.order_by('-test_id')[0].test_id
            test_id = str(int(test_id) + 1)
        except Exception as e:
            print "创建test_id 10000001" + str(e)
            test_id = "10000001"
        # 记录本次测试参数
        if message["test_wait"] is True:
            message.setdefault('status', '4')
        else:
            message.setdefault('status', '1')
        case_type = case_id.split('_')[0]
        try:
            public_methods.inert_tastframe(
                test_id,
                case_id,
                case_type,
                message['tableName'],
                message['version'],
                message['status'],
                message["start_time"]
            )
        except Exception as e:
            print "next" + str(e)
        # 判断状态为4的话等待300秒，否则不等待。
        valid = mysql_db.TestFrame.objects.get(test_id=test_id)
        if valid.state == "4":
            time.sleep(300)
            valid.state = "1"
            valid.save()
        # 数据表名称
        sql_table_name = table_name.split(".")[0]
        database = MySQLdb.connect(host="localhost", user="root", passwd="123456", db="test", charset="utf8")
        cursor = database.cursor()
        sql_find = "select * from " + sql_table_name + " where id = " + "'" + case_id + "'"
        sql_result = cursor.execute(sql_find)
        sql_find_list = cursor.fetchmany(sql_result)
        sql_next_id = sql_find_list[0][5]
        # 获取next_id列表
        if sql_next_id == "[0]":
            next_id_list = [case_id]
        else:
            next_id_list = public_methods.get_next_caseid(sql_next_id)

        # 判断测试类型打开不同测试类型所需要的文件，避免在循环中重复打开大文件．
        if case_type == "nlp":
            config = ConfigParser.ConfigParser()
            config.readfp(open('/opt/test/xiangmu3/TestFrame/testservice.ini'))
            path = config.get("TEST_RESULT", "path")
            tool_path = config.get("TEST_RESULT", "nlptool_path")
            case_path = str(path) + "/" + message['version'] + "-" + test_id
            os.system("mkdir " + case_path)
            os.system("cp -rf " + tool_path + " " + case_path)
            return_faillog = open(case_path + "/return_log.txt", "a+")
            test_result = open(case_path + "/result.txt", "a+")
            main_test(times, next_id_list, sql_table_name, cursor, test_id, case_type,
                      message, case_path, return_faillog, test_result)
            return_faillog.close()
            test_result.close()
        else:
            main_test(times, next_id_list, sql_table_name, cursor, test_id, case_type, message, "", "", "")

        # close cursor and database
        cursor.close()
        database.close()
        # in case_path
        os.chdir(case_path)
        # super butt
        super_butt.final_butt(test_id, case_type, times, message)
        # send email
        if mail_valid == "0":
            send_email.send_email_manager(message, test_id)
        else:
            print ("不发送邮件")
    except:
        logger.exception("Exception Logged")


def main_test(times, next_id_list, sql_table_name, cursor, test_id, case_type, message, case_path, flog, test_result):
    # 外层循环－－－－－－－－－－－count
    for count in range(1, int(times) + 1):
        count = str(count)
        if case_type == "nlp":
            flog.write("------------------------------------------------"
                       + '第' + str(count) + '轮测试'
                       + "------------------------------------------------\n")
            test_result.write("-----------------------------------------------------------------"
                              + test_id + " " + '第' + str(count) + '轮测试'
                              + "------------------------------------------------------------"
                              + "\n"
                              )
        # 内层内层－－－－－－－－－－case_id
        for case_id in next_id_list:
            if shun_test_id == test_id:
                print test_id + " has been kill !!!"
                return
            # 数据表查询
            sql_run = "select * from " + sql_table_name + " where id = " + "'" + case_id + "'"
            sql_run_result = cursor.execute(sql_run)
            sql_run_result_list = cursor.fetchmany(sql_run_result)
            # 通过case_id从数据表中获取对应进行取值
            scene = sql_run_result_list[0][1]
            test_case = sql_run_result_list[0][2].strip()
            data = eval(sql_run_result_list[0][3].strip())
            test_tools = sql_run_result_list[0][4]
            test_refs = sql_run_result_list[0][6].strip()
            explain = sql_run_result_list[0][7]
            try:
                port = sql_run_result_list[0][8]
            except Exception as e:
                print "在表格中查询port－－" + str(e)
                pass

            # 在执行工具前，将当前执行的用例存入数据库
            public_methods.insert_test_frame_speed(count, case_id, test_id)

            # 判断测试类型，执行相应的测试方法
            if case_type == "asr":
                asrtest.AsrTest(message, test_case, test_id, data, test_tools, explain, test_refs)
            elif case_type == "nlu":
                nlutest.NluTest(message, test_case, test_id, data, test_tools, explain, port, test_refs)
            elif case_type == "nlp":
                nlptest.NlpTest(message, case_id, test_case, test_refs,
                                test_id, test_tools, explain, scene, count, case_path, flog, test_result)
            else:
                print ("暂不支持的测试类型")


def shut_down(request):
    global shun_test_id
    shun_test_id = request.GET.get("test_id")
    valid = mysql_db.TestFrame.objects.get(test_id=shun_test_id)
    valid.state = '3'
    valid.save()
    return redirect("/test_task1")
