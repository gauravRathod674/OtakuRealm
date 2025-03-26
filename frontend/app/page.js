"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import ImageSlider from "@/components/ImageSlider";
import TopSectionList from "@/components/TopSectionList";
import NewSectionList from "@/components/NewSectionList";
import GenresList from "@/components/GenresList";
import MostViewed from "@/components/MostViewed";
import TrendingCarousel from "@/components/TrendingCarousel";

export default function HomePage() {
  const [homepageData, setHomepageData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    axios
      .get(`${process.env.NEXT_PUBLIC_API_URL}/`)
      .then((response) => {
        setHomepageData(response.data);
      })
      .catch((err) => {
        console.error("Error fetching homepage data:", err);
        setError("Error fetching homepage data");
      });
  }, []);

  if (error) return <div>{error}</div>;
  if (!homepageData) return <div>Loading...</div>;

  return (
    <main className="p-4 bg-black min-h-screen text-white">

      {/* Slider */}
      <ImageSlider sliderData={homepageData.image_slider} />
      <TrendingCarousel trendingData={homepageData.trending_anime} />

      {/* First Row: 4 Sections */}
      <div className="my-8 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {homepageData.top_sections.map((sectionData, idx) => (
          <TopSectionList key={idx} sectionData={sectionData} />
        ))}
      </div>

      {/* Second Row: Two-Column Layout */}
      <div className="flex flex-col lg:flex-row gap-4">
        {/* Left Column (75% width) */}
        <div className="lg:w-3/4 flex flex-col gap-4">
          {homepageData.latest_new_upcoming.map((sectionData, idx) => (
            <NewSectionList key={idx} sectionData={sectionData} />
          ))}
        </div>

        {/* Right Column (25% width) */}
        <div className="lg:w-1/4 flex flex-col gap-4">
          <GenresList genres={homepageData.genres} />
          <MostViewed mostViewed={homepageData.most_viewed} />
        </div>
      </div>

    </main>
  );
}
