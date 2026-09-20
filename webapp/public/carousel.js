// 首页轮播渐进增强（SPEC-001-F05）：v1 等价转写（ADR-0007 SSR-first＋最小
// 原生 JS）。public/ 外链＋defer（组件脚本会被 Astro 内联、与严格 CSP 冲突）；
// 内容事实源＝SSR DOM，无 JS/初始化失败时条目自然可达，只控 visibility/controls/timing。
(function () {
  "use strict";

  // PRD §10：切换间隔约 5–6 秒，冻结 5500ms（≥2 项才 autoplay）。
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
    let enhanced = false; // 增强态闸门：回滚后 handler/autoplay 全部 no-op

    // -- 控件（无 JS 时绝不留下不可用的按钮）----
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
    // （R5，#49：高度稳定改由 CSS 槽位锁定保证——HeroCarousel.astro 的
    // line-clamp＋min-height 槽；JS 实测预留会拉伸容器、把导航推出卡外，
    // 已整体移除，见 HeroCarousel.astro 内注释。）
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

    // -- 自动播放（pause 条件聚合判定；恢复重建完整周期，不立即切图）--
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

    // -- 回滚（事务保证）：提交任一步失败→恢复「未增强」SSR 全可见状态后安全
    // return（不显示错误）。
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
        return; // 未增强（含回滚）：不再重建 autoplay
      }
      if (autoplayAllowed()) {
        timer = window.setInterval(function () {
          activate((index + 1) % count);
        }, AUTOPLAY_INTERVAL_MS);
      }
    }

    // 手动导航（到头绕回）；随后按当前 pause 条件重建完整周期（不立即切走、
    // 不永久关闭 autoplay）。
    function goTo(targetIndex) {
      if (!enhanced) {
        return; // 回滚后控件已移除：先于任何 DOM 操作退出
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

    // 暂停/恢复（TASK G）：hover/内部 focus/页面隐藏即暂停；离开/恢复以完整
    // interval 重建。不抢 focus、不加 aria-live。
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

    // reduced-motion 运行时切换：reduce 即停 autoplay（手动切换恒可用）；
    // 标准 change 事件＋旧 WebKit addListener 兼容 guard。
    function onMotionPreferenceChange(event) {
      reducedMotion = event.matches;
      refreshAutoplay();
    }
    if (typeof motionQuery.addEventListener === "function") {
      motionQuery.addEventListener("change", onMotionPreferenceChange);
    } else if (typeof motionQuery.addListener === "function") {
      motionQuery.addListener(onMotionPreferenceChange);
    }

    // -- 事务提交：任一步抛错都进 rollback。
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

  // defer 时 DOM 已解析完毕；此处兜底非 defer 引入场景。
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAll);
  } else {
    initAll();
  }
})();
