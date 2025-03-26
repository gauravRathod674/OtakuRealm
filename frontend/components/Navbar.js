"use client";

import { useState, useEffect } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faSearch, faFilter } from "@fortawesome/free-solid-svg-icons";
import Link from "next/link";

export default function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [mobileSearchOpen, setMobileSearchOpen] = useState(false);

  // Toggle the side menu
  const toggleMenu = () => {
    setMenuOpen(!menuOpen);
  };

  // Toggle the mobile search bar (for screens <700px)
  const toggleMobileSearch = () => {
    setMobileSearchOpen(!mobileSearchOpen);
  };

  // Close mobile search bar when window is resized to >700px
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth > 700 && mobileSearchOpen) {
        setMobileSearchOpen(false);
      }
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [mobileSearchOpen]);

  return (
    <>
      {/* TOP NAVBAR */}
      <nav className="flex items-center bg-[#191919] h-[60px] px-5 py-1.5 font-sans text-white mb-1">
        {/* Left Section: Hamburger + Brand */}
        <div className="flex items-center gap-4">
          {/* Hamburger */}
          <button
            className="flex flex-col gap-[5px] bg-none border-none cursor-pointer focus:outline-none"
            onClick={toggleMenu}
          >
            <span className="w-5 h-[2px] bg-white block"></span>
            <span className="w-5 h-[2px] bg-white block"></span>
            <span className="w-5 h-[2px] bg-white block"></span>
          </button>

          {/* Brand */}
          <div className="text-lg font-bold uppercase"> 
            <Link href="/">
            OtakuRealm
            </Link>
            </div>
        </div>

        {/* Desktop Search Bar (hidden below 700px) */}
        <div className="hidden md:ml-8 md:inline-flex md:items-center md:border md:border-[#191919] md:bg-white md:rounded md:overflow-hidden md:py-[2px]">
          <input
            type="text"
            className="border-none px-2 py-1 text-sm outline-none text-black w-80"
            placeholder="Search anime..."
          />
          <span className="text-[#191919] px-2">
            <i className="fa fa-search"></i>
          </span>
        
          <button className="bg-[#191919] text-white text-sm px-3 py-0.5 rounded hover:bg-[#bb5052] mr-2">
            Filter
            <span className="text-white ml-1 text-xs">
            <FontAwesomeIcon icon={faSearch} />
            </span>
          </button>
        </div>

        {/* Right Side Buttons */}
        <div className="ml-auto flex items-center gap-3">
          {/* Search icon for mobile (only visible below 700px) */}
          <span
            className="text-white text-lg cursor-pointer md:hidden"
            onClick={toggleMobileSearch}
          >
            <i className="fa fa-search"></i>
          </span>

          {/* Chat Now & Login buttons */}
          <button className="bg-[#bb5052] text-black font-semibold px-3 py-1 rounded-lg text-sm hover:bg-[#A04345]">
            Chat Now
          </button>
          <Link href="/login" className="bg-[#bb5052] text-black font-semibold px-3 py-1 rounded-lg text-sm hover:bg-[#A04345]">
            Login
          </Link>
        </div>
      </nav>

      {/* SIDE MENU */}
      <div
        className={`
          fixed top-0 left-0 w-[200px] h-screen bg-[#191919] z-50 transform transition-transform duration-300
          flex flex-col p-5
          ${menuOpen ? "translate-x-0" : "-translate-x-[220px]"}
        `}
      >
        <div
          className="inline-flex items-center bg-[#BB5052] text-white rounded-full px-3 py-2 mb-6 cursor-pointer hover:bg-[#A04345]"
          onClick={toggleMenu}
        >
          <span className="font-semibold mr-2 text-base">{"<"}</span> Close menu
        </div>
        <ul className="flex flex-col space-y-0">
          <li className="text-white text-sm font-semibold py-3 border-b border-[#353535] hover:text-[#bb5052] cursor-pointer">
            Home
          </li>
          <li className="text-white text-sm font-semibold py-3 border-b border-[#353535] hover:text-[#bb5052] cursor-pointer">
            Subbed Anime
          </li>
          <li className="text-white text-sm font-semibold py-3 border-b border-[#353535] hover:text-[#bb5052] cursor-pointer">
            Dubbed Anime
          </li>
          <li className="text-white text-sm font-semibold py-3 border-b border-[#353535] hover:text-[#bb5052] cursor-pointer">
            Most Popular
          </li>
          <li className="text-white text-sm font-semibold py-3 border-b border-[#353535] hover:text-[#bb5052] cursor-pointer">
            Movies
          </li>
          <li className="text-white text-sm font-semibold py-3 border-b border-[#353535] hover:text-[#bb5052] cursor-pointer">
            TV Series
          </li>
        </ul>
      </div>

      {/* Overlay for background dim when side menu is open */}
      {menuOpen && (
        <div
          className="fixed top-0 left-0 w-full h-full bg-black/40 z-40"
          onClick={toggleMenu}
        />
      )}

      {/* MOBILE SEARCH BAR (only visible on small screens) */}
      <div
        className={`
          ${mobileSearchOpen ? "flex" : "hidden"}
          bg-[#191919] px-3 py-2 items-center gap-3 md:hidden
        `}
      >
        {/* Separate Filter Button at the left-end */}
        <button className="w-10 h-10 bg-[#e2e2e2] flex items-center justify-center rounded text-[#191919] text-lg">
          <i className="fa fa-filter"></i>
        </button>
        {/* Mobile Search Container */}
        <div className="flex items-center bg-white rounded flex-1 overflow-hidden">
          <input
            type="text"
            className="flex-1 text-sm px-2 py-1 outline-none text-black"
            placeholder="Search anime..."
          />
          <button className="w-10 h-10 flex items-center justify-center text-[#191919] hover:bg-[#e2e2e2]">
            <i className="fa fa-search"></i>
          </button>
        </div>
      </div>
    </>
  );
}
