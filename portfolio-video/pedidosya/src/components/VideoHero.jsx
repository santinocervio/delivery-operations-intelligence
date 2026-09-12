import { useEffect, useRef, useState } from "react";
import "./video.css";

/**
 * Background hero loop for a project card or page header.
 *
 * The video is only fetched once the element is close to the viewport, playback
 * pauses whenever it scrolls away, and a viewer who asked for reduced motion
 * gets the poster frame instead of a moving image — never both.
 *
 * @param {object} props
 * @param {string} [props.webm]     WebM source (preferred; smaller).
 * @param {string} [props.mp4]      MP4 source (fallback; Safari).
 * @param {string} props.poster     Poster image, also the reduced-motion still.
 * @param {string} [props.alt]      Description of the poster for screen readers.
 * @param {number} [props.rootMargin] Pixels ahead of the viewport to start loading.
 * @param {React.ReactNode} [props.children] Overlay content (headline, links).
 */
export default function VideoHero({
  webm,
  mp4,
  poster,
  alt = "Delivery Operations Intelligence — animated case study still",
  rootMargin = 400,
  children,
}) {
  const holder = useRef(null);
  const video = useRef(null);
  const [shouldLoad, setShouldLoad] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);

  // Respect the OS setting, and keep respecting it if the viewer changes it.
  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => setReducedMotion(query.matches);
    sync();
    query.addEventListener("change", sync);
    return () => query.removeEventListener("change", sync);
  }, []);

  // Load late, and only once.
  useEffect(() => {
    if (reducedMotion || shouldLoad) return undefined;
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
      { rootMargin: `${rootMargin}px` }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [reducedMotion, shouldLoad, rootMargin]);

  // Don't decode frames for a loop nobody is looking at.
  useEffect(() => {
    const node = holder.current;
    const el = video.current;
    if (!node || !el || reducedMotion) return undefined;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const attempt = el.play();
            if (attempt && typeof attempt.catch === "function") attempt.catch(() => {});
          } else {
            el.pause();
          }
        });
      },
      { threshold: 0.1 }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [reducedMotion, shouldLoad]);

  return (
    <div className="dov-hero" ref={holder}>
      {reducedMotion ? (
        <img className="dov-hero__media" src={poster} alt={alt} />
      ) : (
        <video
          ref={video}
          className="dov-hero__media"
          poster={poster}
          autoPlay
          muted
          loop
          playsInline
          preload="none"
          aria-label={alt}
          tabIndex={-1}
        >
          {shouldLoad && webm ? <source src={webm} type="video/webm" /> : null}
          {shouldLoad && mp4 ? <source src={mp4} type="video/mp4" /> : null}
        </video>
      )}
      <div className="dov-hero__scrim" />
      {children ? <div className="dov-hero__content">{children}</div> : null}
    </div>
  );
}
