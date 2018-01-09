# coding=utf-8

from apps.testservice import models as mysql_db
from apps.testservice.views import send_email
import public_methods
import os
import re
import time
import gc


def report_manager(test_result, test_id, message, result_type, count,
                   explain, case_path, test_refs, case_id, flog, test_result_file):

    report_folder = "/part/home/pachiratest/report"
    expected = test_refs
    if result_type == "hawkdecoder":

        hawkdecoder_result(test_result, test_id, message, expected, report_folder, count, explain)

    if result_type == "nlutest":

        nlutest_result(test_result, test_id, message, expected, report_folder, explain)

    if result_type == "nlptest":

        nlptest_result(test_id, explain, case_path, count, case_id, flog, test_result_file)


def hawkdecoder_result(test_result_file, test_id, message, expected, report_folder, count, explain):

    global test_result

    test_result_file = open(test_result_file, "rw")
    lines = test_result_file.readlines()

    rate = lines[6].split("|")[3].split(" ")[1]

    counts = '第' + str(count) + '轮测试'

    if rate >= expected:
        test_result = 'success'
    else:
        test_result = "false"

    print lines

    print test_result
    print test_id
    print message["caseId"]

    report_file = report_folder+"/"+test_id+"report.txt"
    report_file_gbk = report_folder + "/" + test_id + "report_gbk.txt"

    try:
        os.system("touch " + report_folder + "/" + test_id + "report.txt")
        o_report_file = open(report_file, "a")
        o_report_file.write(explain)
        o_report_file.write("\n")
        o_report_file.write("--------------------------------" + test_id + ' ' + str(count)
                            + "----------------------------------")

    except:

        o_report_file = open(report_file, "a")

    o_report_file.write("\n")
    o_report_file.write(message["caseId"]+test_result)
    o_report_file.write("\n")
    o_report_file.write(counts)
    o_report_file.write("\n")
    o_report_file.write("句正确率:"+rate)
    o_report_file.write("\n")
    for i in range(1, len(lines)):
        o_report_file.write(lines[i])

    o_report_file.close()
    os.system("iconv -c -f utf-8 -t gbk " + report_file + " >" + report_file_gbk)
    print "iconv -c -f utf-8 -t gbk " + report_file + " >" + report_file_gbk


def nlutest_result(test_result_file, test_id, message, expected, report_folder, explain):
    pwd = os.getcwd()
    print pwd
    global test_result

    test_result_file = open(test_result_file, "rw")
    lines = test_result_file.readlines()
    falses = 0
    trues = 0

    for line in lines:
        if line[-2] == '1':
            falses = falses + 1
        else:
            trues = trues + 1
    if falses > 0:
        test_result = "false"
    else:
        test_result = "true"

    sums = falses + trues
    print "---------------------"+str(sums)+","+str(trues)
    valid = str(float(trues)/sums)

    excepted = str(expected)[-3]

    report_file = report_folder + "/" + test_id + "report.txt"
    report_file_gbk = report_folder + "/" + test_id + "report_gbk.txt"
    try:
        os.system("touch " + report_folder + "/" + test_id + "report.txt")
        public_methods.insert_table(test_id, report_folder + "/" + test_id + "report", "resultPath", "")
        o_report_file = open(report_file, "a")
        o_report_file.write(explain)
        o_report_file.write("\n")
        o_report_file.write("--------------------------------" + test_id + "----------------------------------")

    except:

        o_report_file = open(report_file, "a")

    o_report_file.write("\n")
    o_report_file.write(message["caseId"] + ' -- ' + test_result)
    o_report_file.write("\n")
    o_report_file.write("期望值:" + ' ' + excepted)
    o_report_file.write("\n")
    o_report_file.write("正确率:" + ' ' + str(valid))
    o_report_file.write("\n")
    o_report_file.write("正确个数: " + str(trues) + ' ' + "失败个数:" + str(falses))
    o_report_file.write("\n\n")
    o_report_file.write("错误的有:")
    o_report_file.write("\n")
    for line in lines:
        if line[-2] == '1':
            o_report_file.write(line)

    o_report_file.close()

    os.system("iconv -f utf-8 -t gbk " + report_file + " >" + report_file_gbk)


def nlptest_result(test_id, explain, casepath, count, case_id, flog, test_result_file):
    logger, fh, ch = public_methods.set_logger()
    '''统计一次测试完成后成功和失败的个数　true_count ; faile_count '''
    true_count = 0
    faile_count = 0
    # 统计轮测试数
    counts = '第' + str(count) + '轮测试'
    # 打开结果文件,计算正确和错误
    compare_result = open(casepath + "/test/compare_result.txt", "r")
    for line in compare_result:
        if "测试成功" in line:
            true_count += 1
        elif "测试失败" in line:
            faile_count += 1
    compare_result.close()
    # 将本次测试结果记录到log
    if faile_count == 0:
        logger.info(counts + " 用例:" + case_id + "测试成功")
    else:
        logger.info(counts + " 用例:" + case_id + "测试失败")

    '''执行之后将其中的错误的报告写入到文件中'''
    return_fail = open(casepath + "/test/return_result_fail.txt")
    flog.write(return_fail.read())
    return_fail.close()

    # 获取nlp－count数据库4
    try:
        nlp_count = mysql_db.NlpCount.objects.get(test_id=test_id, count=str(count))
    except Exception as e:
        print e
        nlp_valid = mysql_db.NlpCount(test_id=test_id, count=count, nlp_true=0, nlp_fail=0)
        nlp_valid.save()
        nlp_count = mysql_db.NlpCount.objects.get(test_id=test_id, count=str(count))

    # 用例测试成功--成功将记录到数据库成功个数取出并增加
    if faile_count == 0:
        nlp_count.nlp_true += 1
        nlp_count.save()

    # 用例测试失败--成功将记录到数据库成功个数取出并增加
    elif faile_count != 0:
        nlp_count.nlp_fail += 1
        nlp_count.save()

    # 进入到指定目录下
    # print casepath
    # os.chdir(casepath)

    # 正则表达式选取错误结果写入报告
    compare_result = open(casepath + "/test/compare_result.txt", "r")
    result_read = compare_result.read()
    result = re.findall(">>>[\s\S]*?<<<", str(result_read))
    for i in result:
        if "测试失败" in i:
            '''－－－－－－－－－－－－开始进行报告整理－－－－－－－－－－－－－'''
            test_result_file.write("\n")
            test_result_file.write("-------------------------------------------------------"
                                   + str(case_id)
                                   + "--------------------------------------------------")
            test_result_file.write("\n")
            test_result_file.write("说明 : " + explain)
            test_result_file.write("\n")
            test_result_file.write("结果 : " + str(case_id) + counts + "失败")
            test_result_file.write("\n")
            test_result_file.write("正确个数为 : " + str(true_count) + '    ' + "失败个数为 : " + str(faile_count))
            test_result_file.write("\n")
            test_result_file.write("测试失败的字段如下 : ")
            test_result_file.write("\n\n")
            test_result_file.write(i)
            test_result_file.write("\n")
    test_result_file.write("\n")
    compare_result.close()




