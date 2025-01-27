# Numpy is the main package for scientific computing with Python.
import glob

import cv2.xfeatures2d
# Matplotlib is a useful plotting library for python
import matplotlib.pyplot as plt

# This code is to make matplotlib figures appear inline in the
# notebook rather than in a new window.

plt.rcParams['figure.figsize'] = (10.0, 8.0)  # set default size of plots, can be changed
plt.rcParams['image.interpolation'] = 'nearest'
plt.rcParams['image.cmap'] = 'gray'


# Some more magic so that the notebook will reload external python modules;
# see http://stackoverflow.com/questions/1907993/autoreload-of-modules-in-ipython


def draw_outline (ref, query, model):
    """
        Draw outline of reference image in the query image.
        This is just an example to show the steps involved.
        You can modify to suit your needs.
        INPUTs:
            ref: reference image
            query: query image
            model: estimated transformation from query to reference image
    """
    h, w = ref.shape[:2]
    pts = np.float32 ([[0, 0], [0, h - 1], [w - 1, h - 1], [w - 1, 0]]).reshape (-1, 1, 2)
    dst = cv2.perspectiveTransform (pts, model)

    img = query.copy ()
    img = cv2.polylines (img, [np.int32 (dst)], True, 255, 10, cv2.LINE_AA)
    plt.imshow (img, 'gray'), plt.show ()


def draw_inliers (img1, img2, kp1, kp2, matches, matchesMask):
    """
        Draw inlier between images
        img1 / img2: reference/query  img
        kp1 / kp2: their keypoints
        matches : list of (good) matches after ratio test
        matchesMask: Inlier mask returned in cv2.findHomography()
    """
    matchesMask = matchesMask.ravel ().tolist ()
    draw_params = dict (
            matchColor=(0, 255, 0),  # draw matches in green color
            singlePointColor=None,
            matchesMask=matchesMask,  # draw only inliers
            flags=2
            )
    img3 = cv2.drawMatches (img1, kp1, img2, kp2, matches, None, **draw_params)
    plt.imshow (img3, 'gray'), plt.show ()


# ----------------------------------------------------------------------------------------------------------------------

def MY_ORB (path, image1, image2, features=500, print_img=True, print_keypoint=True):
    image_Query = cv2.imread (f'./A2_smvs/{path}/Query/{image1}.jpg', cv2.IMREAD_GRAYSCALE)
    image_Reference = cv2.imread (f'./A2_smvs/{path}/Reference/{image1}.jpg', cv2.IMREAD_GRAYSCALE)

    # compute detector and descriptor
    # 创建ORB特征提取器
    orb = cv2.ORB_create (features)

    # find the keypoints and descriptors with ORB
    # 检测关键点
    kp1 = orb.detect (image_Reference, None)
    kp2 = orb.detect (image_Query, None)
    # 计算描述符
    kp1, des1 = orb.compute (image_Reference, kp1)
    kp2, des2 = orb.compute (image_Query, kp2)

    # draw keypoints
    # 对关键点进行可视化
    image_Reference_orb = cv2.drawKeypoints (image_Reference, kp1, None, color=(0, 255, 0), flags=0)
    image_Query_orb = cv2.drawKeypoints (image_Query, kp2, None, color=(0, 255, 0), flags=0)

    # create BFMatcher object
    bf = cv2.BFMatcher (cv2.NORM_HAMMING, crossCheck=False)

    # Match descriptors.
    matches = bf.knnMatch (des1, des2, k=2)

    # Apply ratio test
    # 筛选匹配项(ratio_test,ratio=0.8)
    # 创建子集，并以list的形式存入(一个只包含一个值的list)
    good_match = []
    # 创建子集合，但不创建list
    good_without_list = []
    for (x, y) in matches:
        if x.distance < 0.8 * y.distance:
            good_match.append ([x])
            good_without_list.append (x)

    # draw matches
    result = cv2.drawMatchesKnn (image_Reference, kp1, image_Query, kp2, good_match, outImg=None, flags=2)

    print ('Found', len (good_match), 'matches')

    if print_img:
        if print_keypoint:
            plt.subplot (221)
            plt.imshow (image_Query_orb)
            plt.subplot (222)
            plt.imshow (image_Reference_orb)
            plt.subplot (212)
            plt.imshow (result)
        else:
            plt.imshow (result)
        plt.show ()

    return [image_Reference, image_Query, kp1, des1, kp2, des2, matches, good_match, good_without_list]


# ----------------------------------------------------------------------------------------------------------------------

def findHomography (image_1_kp, image_2_kp, good_matches, ransac_val=5, is_RANSAC=False):
    image_1_points = np.zeros ((len (good_matches), 1, 2), dtype=np.float32)
    image_2_points = np.zeros ((len (good_matches), 1, 2), dtype=np.float32)

    for i in range (0, len (good_matches)):
        image_1_points[i] = image_1_kp[good_matches[i].queryIdx].pt
        image_2_points[i] = image_2_kp[good_matches[i].trainIdx].pt

    if is_RANSAC:
        M, Mask = cv2.findHomography (image_1_points, image_2_points, cv2.RANSAC, ransacReprojThreshold=ransac_val)
    else:
        M, Mask = cv2.findHomography (image_1_points, image_2_points, ransacReprojThreshold=ransac_val)

    return [M, Mask]


# ----------------------------------------------------------------------------------------------------------------------

def outline_inliers (path, image1, image2, ransac_val=5, is_RANSAC=False):
    image_Reference, image_Query, kp1, des1, kp2, des2, matches, good_match, good_without_list = MY_ORB (
            path, image1, image2, print_img=False
            )

    # using regular method (cv2.findHomography)
    M, Mask = findHomography (kp1, kp2, good_without_list, ransac_val, is_RANSAC)
    # draw outline
    draw_outline (image_Reference, image_Query, M)
    # draw inliers
    draw_inliers (image_Reference, image_Query, kp1, kp2, good_without_list, Mask)


# ----------------------------------------------------------------------------------------------------------------------

# 可映射多个值的字典
from collections import defaultdict
import re


def match_score (path, image='', is_extra_picture=False, one_img=False, num_not_repeat=True, is_result_show=True,
                 feature=500,
                 ratio=0.8,
                 k=1):
    if image != '':
        one_img = True

    threshold = 30

    Reference_paths = []
    Query_paths = []

    Reference = []
    Query = []

    temp = []

    if is_extra_picture:
        # 匹配任何内容
        my_re = r'.*'
    else:
        # 正则表达式，仅匹配原有的数据集
        my_re = r'[0-9]{3}'

    # 读取一个Query，用所有Reference进行匹配
    if one_img:
        # 读取Query
        Query.append (cv2.imread (f'./A2_smvs/{path}/Query/{image}.jpg', cv2.IMREAD_GRAYSCALE))
    else:
        # 获取Query图片路径
        Query_paths = glob.glob (f'./A2_smvs/{path}/Query/*.jpg')
        Query_paths.sort ()
        # 读取图片
        for path1 in Query_paths:
            if re.match (my_re, path1[-7:-4]):
                Query.append (cv2.imread (path1, cv2.IMREAD_GRAYSCALE))

    # 获取Reference图片路径
    Reference_paths = glob.glob (f'./A2_smvs/{path}/Reference/*.jpg')
    Reference_paths.sort ()
    # 读取图片
    for path2 in Reference_paths:
        if re.match (my_re, path2[-7:-4]):
            Reference.append (cv2.imread (path2, cv2.IMREAD_GRAYSCALE))

    # print(len(Query))
    # print(len(Reference))
    #
    # print(Reference[0])

    # 创建ORB特征提取器
    orb = cv2.ORB_create (feature)

    # 判断是否是第一次循环
    key = True
    count1 = 0

    success_count = 0

    temp_count = 0

    for i in Query:
        # 是否找到结果
        is_success = False

        # 创建dict,储存（匹配个数，图片名称）
        my_dict = defaultdict (list)
        # 创建list，储存匹配个数(之后需要要排序)
        my_match = []

        max_score = 0
        count2 = 0

        kp1, des1 = orb.detectAndCompute (i, None)

        # 获取Query图片的名称
        if one_img:
            p1 = image
            count1 = 1
        else:
            p1 = Query_paths[count1][-7:-4]
            count1 += 1

        if key:
            for j in Reference:
                is_not_in_dataset = True

                # 检测关键点
                # 计算描述符
                kp2, des2 = orb.detectAndCompute (j, None)

                # create BFMatcher object
                bf = cv2.BFMatcher (cv2.NORM_HAMMING, crossCheck=False)

                matches = bf.knnMatch (des2, des1, 2)

                # 将des2存储,后面节约计算时间
                temp.append (des2)

                # 筛选匹配项(ratio_test,ratio=0.8)
                # 创建子集，并以list的形式存入(一个只包含一个值的list)
                good_match = []

                for (x, y) in matches:
                    if x.distance < ratio * y.distance:
                        good_match.append ([x])

                if len (good_match) > max_score:
                    max_score = len (good_match)
                    p2 = Reference_paths[count2][-7:-4]

                # 储存 {match:p2}
                my_dict[len (good_match)].append (Reference_paths[count2][-7:-4])

                # 储存 [match]
                my_match.append (len (good_match))

                if p1 == Reference_paths[count2][-7:-4]:
                    is_not_in_dataset = False

                count2 += 1

            key = False

        else:
            is_not_in_dataset = True

            for des2 in temp:
                bf = cv2.BFMatcher (cv2.NORM_HAMMING, crossCheck=False)

                # 用储存的 des2 进行匹配，节约计算时间
                matches = bf.knnMatch (des2, des1, 2)

                # 筛选匹配项(ratio_test,ratio=0.8)
                # 创建子集，并以list的形式存入(一个只包含一个值的list)
                good_match = []

                for (x, y) in matches:
                    if x.distance < ratio * y.distance:
                        good_match.append ([x])

                if len (good_match) > max_score:
                    max_score = len (good_match)
                    p2 = Reference_paths[count2][-7:-4]

                # 储存 {match:[p2]}
                my_dict[len (good_match)].append (Reference_paths[count2][-7:-4])

                # 储存 [match]
                my_match.append (len (good_match))

                if p1 == Reference_paths[count2][-7:-4]:
                    is_not_in_dataset = False

                count2 += 1

        # 对my_match进行降序排序
        my_match.sort (reverse=True)

        loop = k

        # 确定循环的次数(相同数字的不算)
        if num_not_repeat:
            new_key = 0
            temp_key = k

            for n in range (1, len (my_match)):
                if temp_key == 0:
                    break
                elif my_match[n] != my_match[n - 1]:
                    temp_key -= 1
                    new_key += 1
                else:
                    new_key += 1
            loop = new_key
            # print ('new_key', new_key)
        #
        # print(my_match)
        # print(my_dict)
        # print('\n')

        # 遍历前k个元素
        for val in range (0, loop):
            # print(my_match[val])
            # print(my_dict[my_match[val]])

            # 调用my_dict,查看其中是否有名字相同的结果
            for x in my_dict[my_match[val]]:
                # print(x)
                if p1 == x:
                    is_success = True
                    max_score = my_match[val]
                    p2 = x

        # print(len(my_match))
        # print('\n')

        if max_score > threshold and is_success:
            success_count += 1
        elif is_success == False and is_not_in_dataset == True:
            success_count += 1

        if is_result_show:
            temp_count += 1
            if max_score > threshold and is_success:
                print ('match successfully:', '<', p1, ' ', p2, '> ', max_score, '\n')
            elif is_success == False and is_not_in_dataset == True:
                print ('not in dataset:    ', '<', p1, ' ', p2, '> ', max_score, '\n')
            elif max_score > threshold and is_success == False:
                print ('match failed:      ', '<', p1, ' ', p2, '> ', max_score, '\n')

    print ('Accuracy: ', float (success_count / count1) * 100, '%')
    # print (temp_count)


# ----------------------------------------------------------------------------------------------------------------------

import numpy as np
from enum import Enum
import time
import cv2
from cv2.xfeatures2d import matchGMS


class DrawingType (Enum):
    ONLY_LINES = 1
    LINES_AND_POINTS = 2
    COLOR_CODED_POINTS_X = 3
    COLOR_CODED_POINTS_Y = 4
    COLOR_CODED_POINTS_XpY = 5


def draw_matches (src1, src2, kp1, kp2, matches, drawing_type):
    height = max (src1.shape[0], src2.shape[0])
    width = src1.shape[1] + src2.shape[1]
    output = np.zeros ((height, width), dtype=np.uint8)
    output[0:src1.shape[0], 0:src1.shape[1]] = src1
    output[0:src2.shape[0], src1.shape[1]:] = src2[:]

    if drawing_type == DrawingType.ONLY_LINES:
        for i in range (len (matches)):
            left = kp1[matches[i].queryIdx].pt
            right = tuple (sum (x) for x in zip (kp2[matches[i].trainIdx].pt, (src1.shape[1], 0)))
            cv2.line (output, tuple (map (int, left)), tuple (map (int, right)), (0, 255, 255))

    elif drawing_type == DrawingType.LINES_AND_POINTS:
        for i in range (len (matches)):
            left = kp1[matches[i].queryIdx].pt
            right = tuple (sum (x) for x in zip (kp2[matches[i].trainIdx].pt, (src1.shape[1], 0)))
            cv2.line (output, tuple (map (int, left)), tuple (map (int, right)), (255, 0, 0))

        for i in range (len (matches)):
            left = kp1[matches[i].queryIdx].pt
            right = tuple (sum (x) for x in zip (kp2[matches[i].trainIdx].pt, (src1.shape[1], 0)))
            cv2.circle (output, tuple (map (int, left)), 1, (0, 255, 255), 2)
            cv2.circle (output, tuple (map (int, right)), 1, (0, 255, 0), 2)

    elif drawing_type == DrawingType.COLOR_CODED_POINTS_X or drawing_type == DrawingType.COLOR_CODED_POINTS_Y or drawing_type == DrawingType.COLOR_CODED_POINTS_XpY:
        _1_255 = np.expand_dims (np.array (range (0, 256), dtype='uint8'), 1)
        _colormap = cv2.applyColorMap (_1_255, cv2.COLORMAP_HSV)

        for i in range (len (matches)):
            left = kp1[matches[i].queryIdx].pt
            right = tuple (sum (x) for x in zip (kp2[matches[i].trainIdx].pt, (src1.shape[1], 0)))

            if drawing_type == DrawingType.COLOR_CODED_POINTS_X:
                colormap_idx = int (left[0] * 256. / src1.shape[1])  # x-gradient
            if drawing_type == DrawingType.COLOR_CODED_POINTS_Y:
                colormap_idx = int (left[1] * 256. / src1.shape[0])  # y-gradient
            if drawing_type == DrawingType.COLOR_CODED_POINTS_XpY:
                colormap_idx = int (
                        (left[0] - src1.shape[1] * .5 + left[1] - src1.shape[0] * .5) * 256. / (
                                src1.shape[0] * .5 + src1.shape[1] * .5)
                        )  # manhattan gradient

            color = tuple (map (int, _colormap[colormap_idx, 0, :]))
            cv2.circle (output, tuple (map (int, left)), 1, color, 2)
            cv2.circle (output, tuple (map (int, right)), 1, color, 2)
    return output


# ----------------------------------------------------------------------------------------------------------------------


def GMS (path, image1, image2):
    img1 = cv2.imread (f'./A2_smvs/{path}/Reference/{image1}.jpg', cv2.IMREAD_GRAYSCALE)
    img2 = cv2.imread (f'./A2_smvs/{path}/query/{image2}.jpg', cv2.IMREAD_GRAYSCALE)

    # img1 = cv2.imread ('./A2_smvs/' + path + '/Reference/' + image1 + '.jpg')
    # img2 = cv2.imread ('./A2_smvs/' + path + '/query/' + image2 + '.jpg')

    orb = cv2.ORB_create (10000)
    orb.setFastThreshold (0)

    kp1, des1 = orb.detectAndCompute (img1, None)
    kp2, des2 = orb.detectAndCompute (img2, None)

    matcher = cv2.BFMatcher (cv2.NORM_HAMMING)
    matches_all = matcher.match (des1, des2)
    start = time.time ()
    matches_gms = matchGMS (
            img1.shape[:2], img2.shape[:2], kp1, kp2, matches_all, withScale=False, withRotation=False,
            thresholdFactor=6
            )
    end = time.time ()
    print ('Found', len (matches_gms), 'matches')
    # print ('GMS takes', end - start, 'seconds')
    output = draw_matches (img1, img2, kp1, kp2, matches_gms, DrawingType.ONLY_LINES)
    plt.imshow (output)
    plt.show ()


# ----------------------------------------------------------------------------------------------------------------------

def auto_match_score (path, image='', is_extra_picture=False, one_img=False, num_not_repeat=True, is_result_show=True,
                      feature=500,
                      ratio=0.8,
                      k=1):
    if image != '':
        one_img = True

    threshold = 30

    Reference_paths = []
    Query_paths = []

    Reference = []
    Query = []

    temp = []

    if is_extra_picture:
        # 匹配任何内容
        my_re = r'.*'
    else:
        # 正则表达式，仅匹配原有的数据集
        my_re = r'[0-9]{3}'

    # 读取一个Query，用所有Reference进行匹配
    if one_img:
        # 读取Query
        Query.append (cv2.imread (f'./A2_smvs/{path}/Query/{image}.jpg', cv2.IMREAD_GRAYSCALE))
    else:
        # 获取Query图片路径
        Query_paths = glob.glob (f'./A2_smvs/{path}/Query/*.jpg')
        Query_paths.sort ()
        # 读取图片
        for path1 in Query_paths:
            if re.match (my_re, path1[-7:-4]):
                Query.append (cv2.imread (path1, cv2.IMREAD_GRAYSCALE))

    # 获取Reference图片路径
    Reference_paths = glob.glob (f'./A2_smvs/{path}/Reference/*.jpg')
    Reference_paths.sort ()
    # 读取图片
    for path2 in Reference_paths:
        if re.match (my_re, path2[-7:-4]):
            Reference.append (cv2.imread (path2, cv2.IMREAD_GRAYSCALE))

    # print(len(Query))
    # print(len(Reference))
    #
    # print(Reference[0])

    # 创建ORB特征提取器
    orb = cv2.ORB_create (feature)

    # 判断是否是第一次循环
    key = True
    count1 = 0

    success_count = 0

    temp_count = 0

    for i in Query:
        # 是否找到结果
        is_success = False

        # 创建dict,储存（匹配个数，图片名称）
        my_dict = defaultdict (list)
        # 创建list，储存匹配个数(之后需要要排序)
        my_match = []

        max_score = 0
        count2 = 0

        kp1, des1 = orb.detectAndCompute (i, None)

        # 获取Query图片的名称
        if one_img:
            p1 = image
            count1 = 1
        else:
            p1 = Query_paths[count1][-7:-4]
            count1 += 1

        if key:
            for j in Reference:
                is_not_in_dataset = True

                # 检测关键点
                # 计算描述符
                kp2, des2 = orb.detectAndCompute (j, None)

                # create BFMatcher object
                bf = cv2.BFMatcher (cv2.NORM_HAMMING, crossCheck=False)

                matches = bf.knnMatch (des2, des1, 2)

                # 将des2存储,后面节约计算时间
                temp.append (des2)

                # 筛选匹配项(ratio_test,ratio=0.8)
                # 创建子集，并以list的形式存入(一个只包含一个值的list)
                good_match = []

                for (x, y) in matches:
                    if x.distance < ratio * y.distance:
                        good_match.append ([x])

                if len (good_match) > max_score:
                    max_score = len (good_match)
                    p2 = Reference_paths[count2][-7:-4]

                # 储存 {match:p2}
                my_dict[len (good_match)].append (Reference_paths[count2][-7:-4])

                # 储存 [match]
                my_match.append (len (good_match))

                if p1 == Reference_paths[count2][-7:-4]:
                    is_not_in_dataset = False

                count2 += 1

            key = False

        else:
            is_not_in_dataset = True

            for des2 in temp:
                bf = cv2.BFMatcher (cv2.NORM_HAMMING, crossCheck=False)

                # 用储存的 des2 进行匹配，节约计算时间
                matches = bf.knnMatch (des2, des1, 2)

                # 筛选匹配项(ratio_test,ratio=0.8)
                # 创建子集，并以list的形式存入(一个只包含一个值的list)
                good_match = []

                for (x, y) in matches:
                    if x.distance < ratio * y.distance:
                        good_match.append ([x])

                if len (good_match) > max_score:
                    max_score = len (good_match)
                    p2 = Reference_paths[count2][-7:-4]

                # 储存 {match:[p2]}
                my_dict[len (good_match)].append (Reference_paths[count2][-7:-4])

                # 储存 [match]
                my_match.append (len (good_match))

                if p1 == Reference_paths[count2][-7:-4]:
                    is_not_in_dataset = False

                count2 += 1

        # 对my_match进行降序排序
        my_match.sort (reverse=True)

        loop = k

        # 确定循环的次数(相同数字的不算)
        if num_not_repeat:
            new_key = 0
            temp_key = k

            for n in range (1, len (my_match)):
                if temp_key == 0:
                    break
                elif my_match[n] != my_match[n - 1]:
                    temp_key -= 1
                    new_key += 1
                else:
                    new_key += 1
            loop = new_key
            # print ('new_key', new_key)
        #
        # print(my_match)
        # print(my_dict)
        # print('\n')

        # 遍历前k个元素
        for val in range (0, loop):
            # print(my_match[val])
            # print(my_dict[my_match[val]])

            # 调用my_dict,查看其中是否有名字相同的结果
            for x in my_dict[my_match[val]]:
                # print(x)
                if p1 == x:
                    is_success = True
                    max_score = my_match[val]
                    p2 = x

        # print(len(my_match))
        # print('\n')

        if max_score > threshold and is_success:
            success_count += 1
        elif is_success == False and is_not_in_dataset == True:
            success_count += 1

    Accuracy = float (success_count / count1)

    return [Accuracy, feature, ratio]


# ----------------------------------------------------------------------------------------------------------------------

def best_match_test (INPUT):
    time1 = time.time ()
    count = 1
    best_parameter = []

    # 参数输入
    with open (f'./logbook/match_record_{INPUT[6]}.txt', 'w') as f:
        for Feature in range (INPUT[0], INPUT[1], INPUT[2]):
            for Ratio in range (INPUT[3], INPUT[4], INPUT[5]):
                Ratio /= 1000

                result = auto_match_score (INPUT[6], feature=Feature, ratio=Ratio, k=5)

                best_parameter.append (result)

                f.write (f'TEST:{count}     Accuracy: {result[0]}     feature:  {result[1]}     ratio:  {result[2]}')
                f.write ('\n')

                print (
                        f'DATA_SET: {INPUT[6]}     TEST:{count}     Accuracy: {result[0]}     feature:  {result[1]}     ratio:  {result[2]} \n'
                        )

                count += 1

    time2 = time.time ()

    print (f'FINISH TIME COST:{time2 - time1} min')

    # 对结果进行排序
    best_parameter.sort (reverse=True)

    # 写入文件
    with open (f'./logbook/best_match_{INPUT[6]}.txt', 'w') as f:
        for out in best_parameter:
            f.write (str (out))
            f.write ('\n')

    print (best_parameter)
# gedit ~/.bashrc export PATH=/home/frank/.local/bin/:$PATH
