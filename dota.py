#!/usr/bin/env python
#FH
###########
# january 12 2018
# wrote a quick script to run out and screen cap squatted domains, 
# 	use mse to find difference in images
#########
import sys
import os
import ConfigParser
from PIL import Image
import StringIO
import datetime
from numpy import array
import numpy as np
import binascii
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

Config = ConfigParser.ConfigParser()
exec_path = os.path.dirname(os.path.realpath(__file__))	
ss_path = os.path.join(exec_path,'ss')

def img_to_hex(img_path):
	with open(img_path, 'r') as f:
		content = f.read()
	return (binascii.hexlify(content))


def find_config(inExec):
	ret_path = os.path.join(inExec,'config.ini')
	return ret_path


def mse(imageA, imageB):
	err = np.sum((imageA.astype("float") - imageB.astype("float"))**2)
	err/=float(imageA.shape[0] * imageA.shape[1])
	return err

def earliest_ss(inPath,ePath):
	os.chdir(inPath)
	files = sorted(os.listdir(inPath), key=os.path.getctime)
	try:
		a = files[-1]
	except Exception as e:
		print "Didn't find a previous image"
		return 0
	path_to_earliest=os.path.join(inPath,a)
	os.chdir(ePath)
	return path_to_earliest

def latest_ss(inPath,ePath):
	os.chdir(inPath)
	files = sorted(os.listdir(inPath), key=os.path.getctime)
	try:
		a = files[0]
	except Exception as e:
		print "Did not find the latest image, something wrong with save vs find pathing ??"
		return 0
	path_to_latest=os.path.join(inPath,a)
	os.chdir(ePath)
	return path_to_latest

def second_latest_ss(inPath,ePath):
	os.chdir(inPath)
	files = sorted(os.listdir(inPath), key=os.path.getctime)
	try:
		a = files[1]
	except Exception as e:
		print "Did not find a second latest image"
		return 0
	path_to_latest=os.path.join(inPath,a)
	os.chdir(ePath)
	return path_to_latest

def write_to_log(value,domain,diff_type,image_url):
	#try:
		log=open("dota_log.csv","a")
		log.write(domain + "," + str(value) + "," + diff_type + "," + image_url + "\n")
		log.close()
	#except:
	#	print "Failed to open log file"

def main():
	#print "Welcome to DNS hunter"
	dcap = dict(DesiredCapabilities.PHANTOMJS)
	dcap["phantomjs.page.settings.userAgent"] = (
   		"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/53 "
    	"(KHTML, like Gecko) Chrome/15.0.87"
	)
	service_args = [
    '--proxy=127.0.0.1:8080',
    '--proxy-type=http',
    ]
#	driver = webdriver.PhantomJS(desired_capabilities=dcap,service_args=service_args)
	driver = webdriver.PhantomJS(desired_capabilities=dcap)

	driver.set_window_size(1366, 728)
	path=find_config(exec_path)
	if path!=0: 
		Config.read(path)		
		domain_list = filter(None,Config.get('domains','list').split(','))

		st = datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')	

		for d in domain_list:
			#print "Testing domain: "+d
			save_path=os.path.join(ss_path,d)
			#does the domain have a folder in ss ? no ? create one
			if not os.path.exists(save_path):
				os.makedirs(save_path) 
				
			#driver go to page, and buffer a ss of the website
			driver.get('http://'+d)
			screen = driver.get_screenshot_as_png()
			#crop the screen and save the image to the appropriate dir
			box = (0, 0, 1366, 728)
			im = Image.open(StringIO.StringIO(screen))
			region = im.crop(box)
			fname='screenshot_'+d+'_'+st+'.png'
			print "Saving screenshot of %s to disk as %s" % (d,fname)
			region.save(os.path.join(save_path,fname), 'PNG', optimize=True, quality=96)

			print "Mean Standard Error (further from 0, more variation) for %s " % d
			#find the earliest and latest files in each path
			e = earliest_ss(save_path, exec_path)
			l = latest_ss(save_path,exec_path)
			l2 = second_latest_ss(save_path,exec_path) 
		

			#open the images, convert to numpy arrays, then pass to mse
			if e!=0 and l!=0:
				print "MSE (Earliest vs Latest)"
				print "opening image %s" % e 	
				early = array(Image.open(e))
				print "opening image %s" % l 	
				latest = array(Image.open(l))
				value = mse(early,latest)
				write_to_log(value,d,"orig","http://sneakypete:443/"+d+"/"+fname)
				print value

			if l2!=0 and l!=0:
				print "MSE (Latest vs 2nd Latest)"
				print "opening image %s" % l2 	
				latest_2nd=array(Image.open(l2))	
				print "opening image %s" % l 	
				latest = array(Image.open(l))
				value = mse(latest_2nd,latest)
				write_to_log(value,d,"recent","http://sneakypete:443/"+d+"/"+fname)
				print value	
			#print "Finished with %s"% d
	
		#print "I feel ya mon"
		exit(0)

	else:
		print "Did not find config.ini in the executing directory"
		exit(0)


if __name__=="__main__":
	main()
