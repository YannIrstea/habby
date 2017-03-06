import matplotlib.pyplot as plt

a = [ 874763. ,541760.]
b = [ 874102. ,541098.]
c = [ 875842. ,541488.]
d = [ 874952.7 ,541487.6]
e= [ 874982.9 ,541488. ]


f = [ 875842., 541488.]
g = [ 877538., 541321.]
h = [ 876770., 543246.]
d = [ 875013.1 ,541488.4]
e = [ 874982.9 ,541488. ]

plt.figure()
plt.plot(a[0], a[1], 'r*')
plt.plot(b[0], b[1], 'r*')
plt.plot(c[0], c[1], 'r*')
plt.plot(d[0], d[1], 'b^')
plt.plot(e[0],e[1], 'b^')
plt.plot(f[0], f[1], 'g*')
plt.plot(g[0], g[1], 'g*')
plt.plot(h[0], h[1], 'g*')
plt.show()