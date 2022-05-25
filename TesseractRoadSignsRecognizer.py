# Copyright 2022 antillia.com Toshiyuki Arai 
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# TesseractRoadSignsRecognizer.py
# 
# 2022/05/10 copyright (c) antillia.com

# https://github.com/UB-Mannheim/tesseract/wiki
# https://gammasoft.jp/blog/ocr-by-python/#pyocr
# git clone https://github.com/tesseract-ocr/tessdata_best.git
# See also: https://stackoverflow.com/questions/20831612/getting-the-bounding-box-of-the-recognized-words-using-python-tesseract

# -*- coding: utf-8 -*-

import os
from re import S
import sys
import glob
from PIL import Image
import cv2
import pytesseract
from pytesseract import Output
import traceback
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity 
import numpy as np 
import json
from CosineSimilarity import CosineSimilarity


class TesseractRoadSignsRecognizer:

  def __init__(self, anno_file, lang = 'eng'):

    self.annotation_file = anno_file  # json file
    self.load_annotation_file()

    self.lang = lang
    print("We use lang '%s'" % (self.lang))

    self.config = '--psm 6'


  def is_roadsigns_name(self, t):
    # Checking text t is acceptable name as the roadsigns.
    rc = False
    if len(t) >0:
      if t.isdecimal() or t.isupper(): #not t.islower():
        rc= True
    return rc

  def get_string_list(self, img):
    dic  = pytesseract.image_to_data(img, lang=self.lang, output_type=Output.DICT, config=self.config)

    text = dic['text']
    #print(boxes)
    strings = []
    if len(text)>0:
      for t in text:
        if self.is_roadsigns_name(t):
          strings.append(t)
    return strings, dic

  def to_double_quote(self, vec):
    s = []
    for v in vec:
     print(v)
     x = '"' + v + '"'
     s.append(x)
    return S

  def load_annotation_file(self):
    self.annotation = None
    with open(self.annotation_file, 'r') as json_file:
       self.annotation = json.load(json_file)
    print(self.annotation)
    self.roadsigns = self.annotation["roadsigns"]
    for sign in self.roadsigns:
      class_name = sign["class_name"]
      strings    = sign["strings"]
      print(" ---- {} {}".format(class_name, strings))

    
  def list_to_string(self, list):
    string = ""
    for l in list:
      string = string + l + " "
    return string

  def compute_similarity(self, strings_list):
    cos_sim    = 0
    cname      = ""
    annotation = ""
    similarity = CosineSimilarity()
    if len(strings_list) != 0:
      strings    = self.list_to_string(strings_list)

      for sign in self.roadsigns:
        class_name   = sign["class_name"]
        anno_strings_list = sign["strings"]
        if len(anno_strings_list) >0:
          anno_strings = self.list_to_string(anno_strings_list)
          #print("====================------------{} {}".format(anno_strings, strings))
          sim = similarity.compute(anno_strings, strings)
          if sim > cos_sim:
            cname      = class_name
            cos_sim    = sim
            annotation = anno_strings

    #print("--- compute_similarity {} {} {}".format(annotation, cname, cos_sim))
    return (annotation, cname, cos_sim)
    
  
  def write_bounding_boxes(self, img, d, string_list, output_file):
    n_boxes = len(d['level'])
    xmin = 4000
    ymin = 4000
    xmax = 0
    ymax = 0

    if len(string_list) >0:

      for i in range(n_boxes):
        if(d['text'][i] != ""):
          (x, y, w, h) = (d['left'][i], d['top'][i], d['width'][i], d['height'][i])
          #cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0, 255), 2)
          if x < xmin:
            xmin = x
          if y < ymin:
            ymin = y
          if (x+w) > xmax:
            xmax = x+w
          if (y+h) > ymax:
            ymax = y+h
      cv2.rectangle(img, (xmin, ymin), (xmax, ymax), (0, 255, 0, 255), 2)
    
    cv2.imwrite(output_file, img)

  # recognize
  def run(self, images_dir, output_dir):

    files  = glob.glob( images_dir + "/*.jpg")
    files += glob.glob( images_dir + "/*.png")
    COLON = ': '
    CONMA = ','
    NL = "\n"
    
    for file in files:
      basename = os.path.basename(file)
      fname    = basename.split(".")[0]

      output_file = os.path.join(output_dir, fname + ".txt")
      with open(output_file, "w", encoding='UTF-8') as f:
        img = None
        if file.endswith(".png"):
          img = cv2.imread(file, cv2.IMREAD_UNCHANGED)
        else:
          img = cv2.imread(file) #, cv2.COLOR_BGR2GRAY)
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        rev = 255 - gray
        #rev = gray
        #rev2 = img -128
        filename = os.path.basename(file)
        #boxes = pytesseract.image_to_boxes(img) 
        #dic     = pytesseract.image_to_data(img, lang=self.lang, output_type=Output.DICT, config='--psm 6')
        list1, dic1 = self.get_string_list(img)
        list2, dic2 = self.get_string_list(rev)
        string_list = list1
        rec_dic     = dic1
        if len(list2) > len(list1):
          string_list = list2
          rec_dic     = dic2
        (annotation, cname, cos_sim) = self.compute_similarity(string_list)

        #print("--- filename {}  result {}".format(filename, result))
        #result = self.to_double_quote(result)
        #print("--- filename {}  result {}".format(filename, result))
        output_image_file = os.path.join(output_dir, filename)
        self.write_bounding_boxes(img, rec_dic, string_list, output_image_file)
        line = basename + CONMA + str(string_list) + CONMA + cname + CONMA + str(cos_sim)

        print(line)
        f.writelines(line + NL)



# python  TesseractRoadSignsRecognizer.py ./sample  ./annotation/roadsigns160.json ./detection

if __name__ == "__main__":
  images_dir   = ""
  anno_file    = ""
  output_dir   = ""
  try:
    if len(sys.argv) == 4:
      images_dir   = sys.argv[1]
      anno_file    = sys.argv[2]
      output_dir   = sys.argv[3]
    else:
      raise Exception("Invalid argument")

    if not os.path.exists(images_dir):
      raise Exception("Not found images_dir " + images_dir)

    if not os.path.exists(anno_file):
      raise Exception("Not found annotation file " + anno_file)

    if not os.path.exists(output_dir):
      os.makedirs(output_dir)
    
    recognizer = TesseractRoadSignsRecognizer(anno_file)
 
    recognizer.run(images_dir, output_dir)

  except:
    traceback.print_exc()

   
