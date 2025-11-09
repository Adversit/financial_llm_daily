document.addEventListener("DOMContentLoaded", () => {
  const otpForm = document.querySelector('form[data-role="otp-request"]');
  if (otpForm) {
    const statusEl = document.getElementById("otp-status");
    otpForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!statusEl) return;
      statusEl.classList.remove("text-red-600", "text-green-600");
      statusEl.textContent = "正在发送验证码...";
      statusEl.classList.remove("hidden");
      try {
        const resp = await fetch(otpForm.action, {
          method: "POST",
          body: new FormData(otpForm),
        });
        const data = await resp.json();
        if (data.success) {
          statusEl.textContent = data.message || "验证码已发送";
          statusEl.classList.add("text-green-600");
        } else {
          statusEl.textContent = data.error || "发送失败，请稍后再试";
          statusEl.classList.add("text-red-600");
        }
      } catch (error) {
        statusEl.textContent = "发送失败，请检查网络连接";
        statusEl.classList.add("text-red-600");
      }
    });
  }
});
