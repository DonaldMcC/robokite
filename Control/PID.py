class PID:
    def __init__(self, Kp=1, Ki=0.1, Kd=1, maxIntegralCorrection=0, minIntegralCorrection=-0):
        self.Kp = Kp # Proportional gain
        self.Ki = Ki # Integral gain
        self.Kd = Kd # Derivative gain
        self.integral = 0
	self.maxOutput = 1
	self.minOutput = -1
    def incrementTime(self, error, dt):
        self.integral = self.integral + error*self.Ki*dt
    def computeCorrection(self, error, derror):
        correction = self.Kp*(error) + self.Kd*derror + self.integral
        correction = min(max(correction, self.minOutput), self.maxOutput)
        return correction
