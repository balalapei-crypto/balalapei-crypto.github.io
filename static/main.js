/* Home hero: five book covers that swap, one at a time, through all 30 covers. */
(function () {
  var wrap = document.querySelector('.media.covers');
  if (!wrap) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  var all = wrap.getAttribute('data-covers').split(',');
  var books = Array.prototype.slice.call(wrap.querySelectorAll('.book'));
  var shown = books.map(function (b) { return b.querySelector('img.on').getAttribute('src'); });
  var queue = [];

  function shuffle(a) {
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }
  function nextCover() {
    if (!queue.length) {
      queue = shuffle(all.filter(function (c) { return shown.indexOf(c) === -1; }));
    }
    var c = queue.pop();
    return shown.indexOf(c) === -1 ? c : nextCover();
  }

  var turn = 0;
  function swap() {
    var visible = books.filter(function (b) { return b.offsetParent !== null; });
    if (!visible.length) return;
    var book = visible[turn % visible.length];
    var idx = books.indexOf(book);
    turn++;
    var src = nextCover();
    var on = book.querySelector('img.on');
    var off = book.querySelector('img.off');
    var pre = new Image();
    pre.onload = function () {
      off.src = src;
      off.className = 'on';
      on.className = 'off';
      shown[idx] = src;
    };
    pre.src = src;
  }

  // start after the page has loaded so the 30 covers don't compete with first paint
  window.addEventListener('load', function () {
    setTimeout(function () {
      swap();
      setInterval(swap, 1800);
    }, 1500);
  });
})();

/* Photo carousel: crossfade every 3.5 s, dots to jump, pauses while hovered. */
(function () {
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  Array.prototype.forEach.call(document.querySelectorAll('[data-carousel]'), function (el) {
    var slides = el.querySelectorAll('.slide');
    var dots = el.querySelectorAll('.dots button');
    var i = 0, timer = null;
    function show(n) {
      slides[i].classList.remove('on'); dots[i].classList.remove('on');
      i = (n + slides.length) % slides.length;
      slides[i].classList.add('on'); dots[i].classList.add('on');
    }
    function start() { if (!reduce && !timer) timer = setInterval(function () { show(i + 1); }, 3500); }
    function stop() { clearInterval(timer); timer = null; }
    Array.prototype.forEach.call(dots, function (d, k) { d.addEventListener('click', function () { show(k); }); });
    el.addEventListener('mouseenter', stop);
    el.addEventListener('mouseleave', start);
    start();
  });

  /* Card fan: every few seconds one card is drawn up out of the fan, shown larger, then slips back. */
  Array.prototype.forEach.call(document.querySelectorAll('[data-stack]'), function (el) {
    var cards = Array.prototype.slice.call(el.querySelectorAll('.scard'));
    var cur = -1, timer = null, back = null;
    function release() {
      clearTimeout(back);
      cards.forEach(function (c) { c.classList.remove('drawn'); });
      el.classList.remove('has-drawn');
    }
    function draw(i) {
      release();
      cur = i;
      cards[i].classList.add('drawn');
      el.classList.add('has-drawn');
      back = setTimeout(release, 2400);
    }
    function next() {
      var i;
      do { i = Math.floor(Math.random() * cards.length); } while (i === cur && cards.length > 1);
      draw(i);
    }
    cards.forEach(function (c, i) {
      c.addEventListener('click', function () { c.classList.contains('drawn') ? release() : draw(i); });
    });
    if (reduce) return;
    function start() { if (!timer) timer = setInterval(next, 4000); }
    function stop() { clearInterval(timer); timer = null; }
    el.addEventListener('mouseenter', stop);
    el.addEventListener('mouseleave', function () { release(); start(); });
    setTimeout(function () { next(); start(); }, 800);
  });
})();

/* Videos: play only while on screen (saves battery and data); show controls instead if motion is reduced. */
(function () {
  var vids = document.querySelectorAll('video.autovid');
  if (!vids.length) return;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce || !('IntersectionObserver' in window)) {
    Array.prototype.forEach.call(vids, function (v) { v.controls = true; v.removeAttribute('loop'); });
    return;
  }
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      var v = e.target;
      if (e.isIntersecting) { var p = v.play(); if (p && p.catch) p.catch(function () {}); }
      else v.pause();
    });
  }, { threshold: 0.25 });
  Array.prototype.forEach.call(vids, function (v) { io.observe(v); });
})();

/* Flip calendar: hold each page, then turn it while the calendar is visible. */
(function () {
  if (!('IntersectionObserver' in window)) return;
  var motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  var holdTime = 4000;

  Array.prototype.forEach.call(document.querySelectorAll('[data-flipcal]'), function (el) {
    var pages = el.querySelectorAll('.fpage');
    if (pages.length < 2) return;

    var current = 0, timer = null, incoming = null, onScreen = false;

    function hold() {
      timer = setTimeout(function () {
        timer = null;
        var next = (current + 1) % pages.length;
        var image = pages[next].querySelector('img');
        if (!image.complete || !image.naturalWidth) {
          hold();
          return;
        }
        incoming = next;
        pages[next].classList.add('is-next');
        pages[current].classList.add('is-turning');
      }, holdTime);
    }

    function sync() {
      var playing = onScreen && !document.hidden && !motion.matches;
      el.classList.toggle('is-playing', playing);
      if (!playing) {
        clearTimeout(timer);
        timer = null;
      } else if (timer === null && incoming === null) {
        hold();
      }
    }

    el.addEventListener('animationend', function (event) {
      if (event.target !== pages[current] || event.animationName !== 'flipcal-turn' || incoming === null) return;
      pages[current].classList.remove('is-current', 'is-turning');
      pages[current].setAttribute('aria-hidden', 'true');
      current = incoming;
      incoming = null;
      pages[current].classList.replace('is-next', 'is-current');
      pages[current].removeAttribute('aria-hidden');
      sync();
    });

    motion.addEventListener('change', function () {
      if (motion.matches) {
        pages[current].classList.remove('is-current', 'is-turning');
        pages[current].setAttribute('aria-hidden', 'true');
        if (incoming !== null) pages[incoming].classList.remove('is-next');
        current = 0;
        incoming = null;
        pages[0].classList.add('is-current');
        pages[0].removeAttribute('aria-hidden');
      }
      sync();
    });
    document.addEventListener('visibilitychange', sync);
    new IntersectionObserver(function (entries) {
      onScreen = entries[entries.length - 1].intersectionRatio >= .01;
      sync();
    }, { threshold: .01 }).observe(el);
  });
})();
