function [ Sxx, faxis ] = calcFFT(x, Fs)
%PLOTFFT Summary of this function goes here
%   Detailed explanation goes here

fftX = fft(x);
P2 = abs(fftX/length(x));
faxis = P2(1:round(length(x)/2)+1);
faxis(2:end-1) = 2*faxis(2:end-1);
Sxx = Fs*(0:round(length(x)/2))/length(x);
%plot(Sxx,faxis);
%title('Single-Sided Amplitude Spectrum of X(t)');
%xlabel('f (Hz)');
%ylabel('|P1(f)|');


end

