"use client";
// If you're on Next.js 13 (app router), you may need "use client" for client-side rendering

import React, { useState, useEffect } from "react";

// Import FontAwesome
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faAngleLeft,
  faAngleRight,
  faPlayCircle,
  faClosedCaptioning,
  faMicrophone,
  faPlay,
} from "@fortawesome/free-solid-svg-icons";
import Link from "next/link";

/**
 * sliderData structure (each item):
 * {
 *   "spotlight": "#1 Spotlight",
 *   "title": "Solo Leveling Season 2: Arise from the Shadow",
 *   "poster": "https://some-image.jpg",
 *   "detail_url": "/solo-leveling-season-2-arise-from-the-shadow-19413",
 *   "description": "The second season ...",
 *   "film_stats": {
 *     "subtitles": "11",
 *     "dubbing": "9",
 *     "episodes": "13",
 *     "type": "TV",
 *     "runtime": "24m"
 *   }
 * }
 */

const ImageSlider = ({ sliderData = [] }) => {
  const [slideIndex, setSlideIndex] = useState(0);

  // Change slide with wrap-around
  const changeSlide = (newIndex) => {
    if (newIndex < 0) {
      setSlideIndex(sliderData.length - 1);
    } else if (newIndex >= sliderData.length) {
      setSlideIndex(0);
    } else {
      setSlideIndex(newIndex);
    }
  };

  // Auto-slide every 5 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      changeSlide(slideIndex + 1);
    }, 5000);
    return () => clearInterval(interval);
  }, [slideIndex]);

  if (!sliderData.length) return null;

  return (
    <div className="relative flex w-full h-[70vh] overflow-hidden bg-black text-white ">
      {/* Slides */}
      {sliderData.map((animeDetail, index) => (
        <div
          key={index}
          className={`absolute w-full h-full transition-opacity duration-1000 ${
            slideIndex === index ? "flex" : "hidden"
          }`}
        >
          {/* Text Content */}
          <div className="absolute z-20 w-1/2 h-full top-0 left-0 p-12 flex flex-col justify-center bg-transparent">
            {/* Spotlight */}
            <div className="mb-5 text-[#ba574f] text-[18px] font-bold">
              {animeDetail.spotlight}
            </div>

            {/* Title */}
            <div className="mb-5 text-3xl font-bold leading-tight">
              {animeDetail.title}
            </div>

            {/* Details (using your snippet) */}
            <div className="mb-5 text-sm">
              <div className="flex items-center text-sm flex-wrap mt-2">
                <div className="flex items-center gap-[2px]">
                  {/* Subtitles */}
                  {animeDetail.film_stats?.subtitles && (
                    <span className="px-1 py-1 bg-green-300 text-black border-l border-white/10 flex items-center gap-1 text-xs font-bold rounded-l-md">
                      <FontAwesomeIcon
                        icon={faClosedCaptioning}
                        className="mr-1"
                      />
                      {animeDetail.film_stats.subtitles}
                    </span>
                  )}

                  {/* Dubbing */}
                  {animeDetail.film_stats?.dubbing && (
                    <span className="px-1 py-1 bg-pink-300 text-black border-l border-white/10 flex items-center gap-1 text-xs font-bold">
                      <FontAwesomeIcon icon={faMicrophone} className="mr-1" />
                      {animeDetail.film_stats.dubbing}
                    </span>
                  )}

                  {animeDetail.film_stats?.episodes && (
                    <span className="bg-[#ffffff40] episode text-white text-xs font-semibold rounded-r-md px-1 py-1">
                      {animeDetail.film_stats.episodes}
                    </span>
                  )}
                </div>

                {/* Dot + Type + Dot + Runtime */}
                <span className="mx-3 h-1 w-1 bg-gray-400 rounded-full inline-block" />
                <span className="py-1 text-white text-base">
                  {animeDetail.film_stats?.type}
                </span>
                <span className="mx-3 h-1 w-1 bg-gray-400 rounded-full inline-block" />
                <span className="py-1 text-white text-base">
                  {animeDetail.film_stats?.runtime}
                </span>
              </div>
            </div>

            {/* Description */}
            <div className="h-20 overflow-hidden mb-4">
              <p className="text-sm font-light line-clamp-3">
                {animeDetail.description}
              </p>
            </div>

            {/* Buttons */}
            <div className="flex gap-3">
              <button className="px-5 py-2 text-lg bg-[#ba574f] text-black rounded-full flex items-center gap-2 hover:bg-[#bb5052]">
              <span className="font-bold mr-2">
                  <FontAwesomeIcon icon={faPlay} />
                </span>
                <Link
                  href={`/watch${animeDetail.detail_url}?title=${encodeURIComponent(
                    animeDetail.title
                  )}&anime_type=${encodeURIComponent(
                    animeDetail.film_stats.type
                  )}`}
                >
                  Watch now
                </Link>
              </button>
              <button className="px-5 py-2 text-lg bg-[rgba(255,255,255,0.2)] text-white rounded-full flex items-center gap-2 hover:bg-[rgba(255,255,255,0.3)]">
              <Link
                  href={`animedetailpage${animeDetail.detail_url}`}
                >
                  Details
                </Link>
                <FontAwesomeIcon icon={faAngleRight} />
              </button>
            </div>
          </div>

          {/* Image (with gradient mask) */}
          <div className="absolute right-0 w-3/4 h-full overflow-hidden">
            <img
              src={animeDetail.poster}
              alt={animeDetail.title}
              className="object-cover w-full h-full opacity-60"
              style={{
                WebkitMaskImage:
                  "linear-gradient(270deg, transparent 0%, black 30%, black 70%, transparent 100%)",
                maskImage:
                  "linear-gradient(270deg, transparent 0%, black 30%, black 70%, transparent 100%)",
              }}
            />
          </div>
        </div>
      ))}

      {/* Navigation Buttons (hidden on small screens) */}
      <button
        className="hidden md:block absolute bottom-2 right-5 text-white bg-[rgba(255,255,255,0.1)] w-10 h-10 rounded-md flex items-center justify-center z-30 hover:bg-[#ba574f]"
        onClick={() => changeSlide(slideIndex - 1)}
      >
        <FontAwesomeIcon icon={faAngleLeft} />
      </button>
      <button
        className="hidden md:block absolute bottom-14 right-5 text-white bg-[rgba(255,255,255,0.1)] w-10 h-10 rounded-md flex items-center justify-center z-30 hover:bg-[#ba574f]"
        onClick={() => changeSlide(slideIndex + 1)}
      >
        <FontAwesomeIcon icon={faAngleRight} />
      </button>

      {/* Slider Nav (small screens only) */}
      <div className="md:hidden absolute top-1/2 right-4 -translate-y-1/2 z-30 flex flex-col">
        {sliderData.map((_, idx) => (
          <button
            key={idx}
            onClick={() => changeSlide(idx)}
            className={`w-3 h-3 rounded-full my-1 transition-colors ${
              slideIndex === idx
                ? "bg-[#ba574f] opacity-100"
                : "bg-[rgba(255,255,255,0.1)] opacity-70 hover:opacity-100"
            }`}
          ></button>
        ))}
      </div>
    </div>
  );
};

export default ImageSlider;
