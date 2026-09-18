// 首页轮播渐进增强（SPEC-001-F05）。v1 static/js/carousel.js 等价转写
// （ADR-0007：SSR-first ＋ 最小原生 JS；var→let/const 等价改写，控制流与
// DOM 效果逐行一致）。以 public/ 静态文件 + defer 引入（v1 同款架构）：
// Astro 会把小组件脚本自动内联进 HTML（无配置可关），与严格 CSP
// （script-src 无 unsafe-inline）冲突，故沿用 v1 的外链脚本形态。
// 内容事实源始终是 SSR DOM（data-carousel / data-carousel-item），本脚本
// 只控制 visibility/controls/timing；无 JS 或初始化失败时条目全部按文档流
// 自然可达。
(function () {
  "use strict";

  // PRD §10：自动切换间隔约 5–6 秒，冻结 5500ms（仅 ≥2 项允许 autoplay）。
  const AUTOPLAY_INTERVAL_MS = 5500;

  function initCarousel(carousel) {
    if (carousel.hasAttribute("data-carousel-enhanced")) {
      return; // 防重复增强
    }

    const slides = Array.from(
      carousel.querySelectorAll("[data-carousel-item]"),
    );
    const count = slides.length;
    if (count === 0) {
      return; // 异常空容器：安全 no-op
    }
    if (count === 1) {
      return; // 单项保持静态，零增强
    }

    let index = 0;
    const dots = [];
    let enhanced = false; // 增强态闸门：回滚后所有 handler/autoplay 安全 no-op

    // -- 控件（仅 ≥2 项由 JS 动态创建：无 JS 时绝不留下不可用的按钮）----
    const prevButton = document.createElement("button");
    prevButton.type = "button";
    prevButton.className = "carousel-prev";
    prevButton.setAttribute("aria-label", "上一张");
    prevButton.textContent = "‹";

    const nextButton = document.createElement("button");
    nextButton.type = "button";
    nextButton.className = "carousel-next";
    nextButton.setAttribute("aria-label", "下一张");
    nextButton.textContent = "›";

    const dotsContainer = document.createElement("div");
    dotsContainer.className = "carousel-dots";
    for (let i = 0; i < count; i++) {
      const dot = document.createElement("button");
      dot.type = "button";
      dot.className = "carousel-dot";
      dot.setAttribute("aria-label", "转到第 " + (i + 1) + " 张");
      dots.push(dot);
      dotsContainer.appendChild(dot);
    }

    const controls = document.createElement("div");
    controls.className = "carousel-controls";
    controls.setAttribute("data-carousel-controls", "");
    controls.appendChild(prevButton);
    controls.appendChild(dotsContainer);
    controls.appendChild(nextButton);

    // -- 切换状态同步：hidden ＋ active class ＋ 圆点 aria-current --------
    function activate(targetIndex) {
      index = targetIndex;
      slides.forEach(function (slide, slideIndex) {
        const active = slideIndex === index;
        slide.hidden = !active;
        slide.classList.toggle("is-active", active);
      });
      dots.forEach(function (dot, dotIndex) {
        if (dotIndex === index) {
          dot.setAttribute("aria-current", "true");
        } else {
          dot.removeAttribute("aria-current");
        }
      });
    }

    // -- 自动播放（pause 条件聚合判定；恢复一律重建完整周期，不立即切图）--
    let timer = null;
    let hovering = false;
    let focusWithin = false;
    let pageHidden = document.hidden; // 页面在隐藏态加载时同样不 autoplay
    const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    let reducedMotion = motionQuery.matches;

    function autoplayAllowed() {
      return !reducedMotion && !hovering && !focusWithin && !pageHidden;
    }

    function stopAutoplay() {
      if (timer !== null) {
        window.clearInterval(timer);
        timer = null;
      }
    }

    // -- 回滚（事务保证）：提交阶段任一步骤失败后，把 DOM 恢复为等价于
    // 「JS 未成功增强」的 SSR 全可见状态，随后安全 return（不显示错误）。
    function rollback() {
      stopAutoplay();
      slides.forEach(function (slide) {
        slide.hidden = false;
        slide.classList.remove("is-active");
      });
      dots.forEach(function (dot) {
        dot.removeAttribute("aria-current");
      });
      if (controls.parentNode === carousel) {
        carousel.removeChild(controls);
      }
      carousel.removeAttribute("data-carousel-enhanced");
      enhanced = false;
    }

    function refreshAutoplay() {
      stopAutoplay();
      if (!enhanced) {
        return; // 未增强（含回滚后）：一律不再重建 autoplay
      }
      if (autoplayAllowed()) {
        timer = window.setInterval(function () {
          activate((index + 1) % count);
        }, AUTOPLAY_INTERVAL_MS);
      }
    }

    // 手动导航（前/后循环到头即绕回）；随后按当前 pause 条件重建完整周期，
    // 避免点击后不足一个间隔就被自动切走，也不永久关闭 autoplay。
    function goTo(targetIndex) {
      if (!enhanced) {
        return; // 回滚后控件已移除，防御性 no-op：先于任何 DOM 操作退出
      }
      activate((targetIndex + count) % count);
      refreshAutoplay();
    }

    prevButton.addEventListener("click", function () {
      goTo(index - 1);
    });
    nextButton.addEventListener("click", function () {
      goTo(index + 1);
    });
    dots.forEach(function (dot, dotIndex) {
      dot.addEventListener("click", function () {
        goTo(dotIndex);
      });
    });

    // 暂停/恢复（TASK G）：hover、内部 keyboard focus、页面隐藏即暂停；
    // 离开/恢复可见即以完整 interval 恢复。不抢 focus、不加 aria-live。
    carousel.addEventListener("mouseenter", function () {
      hovering = true;
      refreshAutoplay();
    });
    carousel.addEventListener("mouseleave", function () {
      hovering = false;
      refreshAutoplay();
    });
    carousel.addEventListener("focusin", function () {
      focusWithin = true;
      refreshAutoplay();
    });
    carousel.addEventListener("focusout", function (event) {
      if (!carousel.contains(event.relatedTarget)) {
        focusWithin = false;
        refreshAutoplay();
      }
    });
    document.addEventListener("visibilitychange", function () {
      pageHidden = document.hidden;
      refreshAutoplay();
    });

    // prefers-reduced-motion 运行时切换：reduce 即停 autoplay（手动切换
    // 恒可用）；现代标准 change 事件＋旧 WebKit addListener 兼容 guard。
    function onMotionPreferenceChange(event) {
      reducedMotion = event.matches;
      refreshAutoplay();
    }
    if (typeof motionQuery.addEventListener === "function") {
      motionQuery.addEventListener("change", onMotionPreferenceChange);
    } else if (typeof motionQuery.addListener === "function") {
      motionQuery.addListener(onMotionPreferenceChange);
    }

    // -- 事务提交：从首个 SSR 可见性改写（activate）起，任一步骤抛错都
    // 进入 rollback，恢复「未增强」的全可见 SSR 状态后安全返回。
    try {
      activate(0);
      carousel.appendChild(controls);
      carousel.setAttribute("data-carousel-enhanced", "");
      enhanced = true;
      refreshAutoplay();
    } catch {
      rollback();
      return;
    }
  }

  function initAll() {
    document.querySelectorAll("[data-carousel]").forEach(initCarousel);
  }

  // defer 加载时 DOM 已解析完毕；此处兼容 guard 兜底非 defer 引入场景。
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAll);
  } else {
    initAll();
  }
})();
