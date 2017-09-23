import numpy as np
import os
import glob
import math
import argparse
import scipy.misc as sm
import scipy.signal as signal
import matplotlib.pyplot as plt
from utils import *

def S2R(frame_dir, frame_num):

	frame_files = glob.glob(frame_dir+"*.png")
	if frame_num == 0:
		frame_num = len(frame_files)
	print("Number of frames to process: "+str(frame_num))
	signal_sr_b = []
	U, sigmas, pulse = [], [], []
	all_d, all_v = [], []

	fs = 25
	windowsize = 3 # secs
	overlap = 2 # secs
	cutoff = 2 # hz

	## process each frame
	for i in range(frame_num):
		frame_fn = frame_files[i]
		img = np.array(sm.imread(frame_fn), dtype=np.float32)
		rows, cols, chn = img.shape
		r, g, b = img[:,:,0], img[:,:,1], img[:,:,2]
		skin_mask = generate_skinmap(img)
		r_masked = r[skin_mask==1]
		g_masked = g[skin_mask==1]
		b_masked = b[skin_mask==1]
		values = np.array([r_masked, g_masked, b_masked])
		if i == 0:
			trace = np.mean(values,axis=1)
		else:
			trace = np.vstack((trace, np.mean(values, axis=1)))

		## spatial RGB correlation
		C = np.matmul(values, values.T) / (rows*cols)
		D, V = np.linalg.eigh(C)
		diag_ele = D
		U_, S_, V_ = np.linalg.svd(C)
		sort_index = np.argsort(diag_ele)[::-1]
		sort_diag = sorted(diag_ele)[::-1]
		V = V[:,sort_index]
		# V[:,0] *= -1

		U.append(V)
		sigmas.append(sort_diag)

		if i > 0:
			rot = [np.matmul(U[i][:,0].T, U[i-1][:,1]), np.matmul(U[i][:,0], U[i-1][:,2])]
			scale = [math.sqrt(sigmas[i][0]/sigmas[i-1][1]), math.sqrt(sigmas[i][0]/sigmas[i-1][2])]
			sr = np.array(scale) * np.array(rot)
			sr_bp = np.matmul(sr, [U[i-1][:,1], U[i-1][:,2]])
			signal_sr_b.append(sr_bp)

		if (i+1)%100 == 0:
			print("%d/%d frames complete" % ((i+1), frame_num))

	signal_sr_b = np.array(signal_sr_b)
	sigma = np.std(signal_sr_b[:,0]) / np.std(signal_sr_b[:,1])

	blocks_one = buffer(signal_sr_b[:,0], windowsize*fs, windowsize*fs-1).T
	blocks_two = buffer(signal_sr_b[:,1], windowsize*fs, windowsize*fs-1).T
	blocks_three = buffer(signal_sr_b[:,2], windowsize*fs, windowsize*fs-1).T

	frames, dim = blocks_one.shape
	for i in range(frames):
		sigma = np.std(blocks_one[i,:])/np.std(blocks_two[i,:])
		p_block = blocks_one[i,:] - sigma*blocks_two[i,:]
		pulse.append(p_block - np.mean(p_block))
	pulse = np.array(pulse)

	## low-pass filter
	fnorm = cutoff / (fs/2.0)
	[b,a] = signal.butter(10, fnorm, 'low')
	p_blocked = signal.filtfilt(b, a, pulse[:,-1])

	raw = trace[:,1]
	raw = signal.filtfilt(b, a, raw)
	raw = raw[1:] - raw[:-1]

	return p_blocked

def main():

	parser = argparse.ArgumentParser()
	parser.add_argument("--frame_num", type=int, default=0, help="How many frames to process")
	args = parser.parse_args()
	
	frame_dir = "/Users/sherry/data_temp/01_01_01_C/"
	# frame_dir = "./data/images/"
	p_blocked = S2R(frame_dir, args.frame_num)
	
	f, pxx = signal.periodogram(p_blocked, 50)
	fig = plt.figure()
	ax1 = fig.add_subplot(221)
	ax1.plot(p_blocked)
	plt.grid()
	ax2 = fig.add_subplot(222)
	ax2.plot(f, [10*math.log10(ele) for ele in pxx])
	ax2.set_xlim([0,25])
	ax2.set_ylim([-100,-50])
	plt.grid()
	ax3 = fig.add_subplot(223)
	f,t,sxx = signal.spectrogram(p_blocked,fs=25,window=signal.get_window('hamming',128),noverlap=120)
	plt.pcolormesh(t,f,sxx)
	plt.grid()
	plt.show()
# plt.plot(raw)
# plt.plot(pulse[:,-1])
# plt.plot(f, [10*math.log10(ele) for ele in pxx])
# plt.plot(p_blocked)
# plt.xlim([0,5])
# plt.grid()
# plt.show()

if __name__=="__main__":
	main()

