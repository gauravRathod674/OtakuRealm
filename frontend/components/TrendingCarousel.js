"use client";
import { useState } from "react";
import Link from "next/link";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import { faGreaterThan, faLessThan } from "@fortawesome/free-solid-svg-icons";

/**
 * Props:
 *   trendingData = [
 *     { number: "01", title: "Wind Breaker", poster: "...", url: "..." },
 *     { number: "02", title: "Dandadan", poster: "...", url: "..." },
 *     ...
 *   ]
 */

export default function TrendingSection({ trendingData = [] }) {
  // We'll show 6 items at a time
  const [startIndex, setStartIndex] = useState(0);

  // Slice out 6 visible items
  const visibleItems = trendingData.slice(startIndex, startIndex + 6);

  // Check if we can go prev/next
  const canGoPrev = startIndex > 0;
  const canGoNext = startIndex + 6 < trendingData.length;

  // Handlers
  const handlePrev = () => {
    if (!canGoPrev) return;
    setStartIndex((prev) => prev - 1);
  };
  const handleNext = () => {
    if (!canGoNext) return;
    setStartIndex((prev) => prev + 1);
  };

  // Helper to truncate the title to 17 characters
  const truncateTitle = (text) => {
    if (!text) return "";
    return text.length > 17 ? text.slice(0, 17) + "..." : text;
  };

  return (
    <div className="trending-section my-8">
      <h2 className="text-2xl font-bold text-[#bb5052] mb-4 ml-2">Trending</h2>

      {/* Carousel wrapper (relative for nav buttons) */}
      <div className="relative p-3 rounded-md overflow-hidden">
        {/* The horizontal list container */}
        <div className="flex gap-5">
          {visibleItems.map((item) => (
            <div
              key={item.number}
              className="relative flex-shrink-0"
              style={{
                // Card width: for example, 220px
                // Adjust to taste. We'll do 220px so the left portion is ~15%, right portion ~85%.
                width: "220px",
                height: "250px", // Example card height
                backgroundColor: "#191919",
                borderRadius: "6px",
                overflow: "hidden",
              }}
            >
              {/* Left portion: 15% width */}
              <div
                className="absolute top-0 left-0 h-full flex flex-col items-center justify-center text-white"
                style={{ width: "15%", backgroundColor: "transparent" }}
              >
                {/* Rank */}
                <div className="text-[#bb5052] text-2xl font-bold absolute bottom-0">
                  {item.number}
                </div>
                {/* Vertical Title (truncated) */}
                <div
                  className="-rotate-90 text-xs font-medium whitespace-nowrap"
                  style={{ width: "max-content" }}
                >
                  {truncateTitle(item.title)}
                </div>
              </div>

              {/* Right portion: 85% width for the poster */}
              <div
                className="absolute top-0 right-0 h-full"
                style={{ width: "85%" }}
              >
                <Link href={`animedetailpage${item.url}`}>
                  <img
                    src={item.poster}
                    alt={item.title}
                    className="w-full h-full object-cover transition-transform duration-300 hover:scale-105"
                  />
                </Link>
              </div>
            </div>
          ))}
        </div>

        {/* Navigation Buttons (right side, stacked vertically, half card height) */}
        <div className="absolute top-1/2 -translate-y-1/2 right-2 flex flex-col gap-3 mt-4">
          {/* Next Button */}
          <button
            onClick={handleNext}
            disabled={!canGoNext}
            className={`w-10 ${
              // half of card height => ~160px
              "h-30"
            } flex items-center justify-center rounded-md
            ${
              canGoNext
                ? "bg-[#353535] hover:bg-[#bb5052] text-white"
                : "bg-[#353535] text-gray-500 cursor-not-allowed"
            }`}
          >
            {/* ">" or icon */}
            <FontAwesomeIcon icon={faGreaterThan} className="mr-1" />

          </button>

          {/* Prev Button */}
          <button
            onClick={handlePrev}
            disabled={!canGoPrev}
            className={`w-10 ${"h-30"} flex items-center justify-center mb-8 rounded-md
            ${
              canGoPrev
                ? "bg-[#353535] hover:bg-[#bb5052] text-white"
                : "bg-[#353535] text-gray-500 cursor-not-allowed"
            }`}
          >
            {/* "<" or icon */}
            <FontAwesomeIcon icon={faLessThan} className="mr-1" />
          </button>
        </div>
      </div>
    </div>
  );
}
