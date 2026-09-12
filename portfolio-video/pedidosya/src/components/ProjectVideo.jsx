import { useEffect, useRef, useState } from "react";
import "./video.css";

/**
 * The 48-second case study, for a project detail page.
 *
 * The film is silent by design, so it can autoplay on view without ever
 * ambushing anyone with sound. Nothing downloads until the viewer scrolls to
 * it. Under `prefers-reduced-motion` the poster is shown with an explicit play
 * control, so motion only ever happens because someone asked for it.
 *
 * @param {object} props
 * @param {string} [props.webm]      WebM source (preferred).
 * @param {string} [props.mp4]       MP4 source (fallback).
 * @param {string} props.poster      Poster image.
 * @param {string} [props.caption]   Line shown under the frame.
 * @param {boolean} [props.autoPlayOnView] Autoplay when scrolled into view (default true).
 */
export default function ProjectVideo({
  webm,
  mp4,
  poster,
  caption = "Delivery Operations Intelligence — 48s case study. Silent by design.",
  autoPlayOnView = true,
}) {
  const holder = useRef(null);
  const video = useRef(null);
  const [shouldLoad, setShouldLoad] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [started, setStarted] = useState(false);

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => setReducedMotion(query.matches);
    sync();
    query.addEventListener("change", sync);
    return () => query.removeEventListener("change", sync);
  }, []);

  useEffect(() => {
    if (shouldLoad) return undefined;
    const node = holder.current;
    if (!node) return undefined;
    if (typeof IntersectionObserver === "undefined") {
      setShouldLoad(true);
      return undefined;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setShouldLoad(true);
          observer.disconnect();
        }
      },
      { rootMargin: "300px" }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [shouldLoad]);

  // Autoplay only when motion is welcome and the frame is actually on screen.
  useEffect(() => {
    const node = holder.current;
    const el = video.current;
    if (!node || !el || reducedMotion || !autoPlayOnView || started) return undefined;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && entry.intersectionRatio > 0.5) {
            const attempt = el.play();
            if (attempt && typeof attempt.catch === "function") attempt.catch(() => {});
          } else if (!entry.isIntersecting) {
            el.pause();
          }
        });
      },
      { threshold: [0, 0.5] }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [reducedMotion, autoPlayOnView, shouldLoad, started]);

  const play = () => {
    setStarted(true);
    setShouldLoad(true);
    const el = video.current;
    if (el) {
      el.controls = true;
      const attempt = el.play();
      if (attempt && typeof attempt.catch === "function") attempt.catch(() => {});
    }
  };

  return (
    <figure className="dov-project" ref={holder}>
      <div className="dov-project__frame">
        <video
          ref={video}
          className="dov-project__media"
          poster={poster}
          muted
          loop={false}
          playsInline
          preload="none"
          controls={reducedMotion ? started : true}
        >
          {shouldLoad && webm ? <source src={webm} type="video/webm" /> : null}
          {shouldLoad && mp4 ? <source src={mp4} type="video/mp4" /> : null}
        </video>

        {reducedMotion && !started ? (
          <button type="button" className="dov-project__play" onClick={play}>
            <span className="dov-project__play-icon" aria-hidden="true" />
            Play the 48-second case study
          </button>
        ) : null}
      </div>
      {caption ? <figcaption className="dov-project__caption">{caption}</figcaption> : null}
    </figure>
  );
}
