"use client";
import React from "react";

export default function Footer({ footerData }) {
  return (
    <footer className="bg-[#191919] text-white px-6 pt-5 pb-0 mt-5">
      {/* Top Section: Logo + (optionally) Social Icons */}
      <div className="flex flex-wrap items-center justify-between">
        <div className="flex items-center gap-5">
          {/* Logo */}
          <div className="pt-1">
            <span className="text-xl font-bold uppercase">OtakuRealm</span>
          </div>

          {/* Social Icons (uncomment if needed)
          <div className="flex gap-4">
            <a href="#" title="Telegram">
              <i className="fa fa-telegram"></i>
            </a>
            <a href="#" title="Discord">
              <i className="fa fa-discord"></i>
            </a>
            <a href="#" title="Twitter">
              <i className="fa fa-twitter"></i>
            </a>
            <a href="#" title="Facebook">
              <i className="fa fa-facebook"></i>
            </a>
            <a href="#" title="YouTube">
              <i className="fa fa-youtube"></i>
            </a>
          </div> */}
        </div>
      </div>

      {/* Horizontal Divider */}
      <div className="border-t border-[#353535] mt-3 mb-5 w-1/3" />

      {/* A–Z List Section */}
      <div className="mb-4">
        {/* Row with the heading + subtitle */}
        <div className="flex items-center gap-2">
          <span className="font-semibold text-base text-white">A-Z LIST</span>
          <span className="inline-block w-px h-5 bg-[#353535] mx-2"></span>
          <span className="text-sm text-[#ccc]">
            Searching anime orders by alphabetical name A to Z.
          </span>
        </div>

        {/* Row with the letters */}
        <div className="flex flex-wrap gap-2 mt-2">
          {footerData?.map((item, index) => (
            <a
              key={index}
              href={item.url}
              className="px-2 py-1 border border-[#353535] rounded text-xs text-[#ccc] cursor-pointer transition-colors duration-200 hover:bg-[#bb5052] hover:text-black"
            >
              {item.text}
            </a>
          ))}
        </div>
      </div>

      {/* Footer Links */}
      <div className="flex flex-wrap gap-6 py-2 mb-3">
        <a
          href="#"
          className="text-xs text-[#ccc] no-underline hover:text-[#bb5052]"
        >
          Terms of service
        </a>
        <a
          href="#"
          className="text-xs text-[#ccc] no-underline hover:text-[#bb5052]"
        >
          DMCA
        </a>
        <a
          href="#"
          className="text-xs text-[#ccc] no-underline hover:text-[#bb5052]"
        >
          Contact
        </a>
        <a
          href="#"
          className="text-xs text-[#ccc] no-underline hover:text-[#bb5052]"
        >
          Sitemap
        </a>
      </div>

      {/* Disclaimers */}
      <div className="text-xs text-[#999] leading-5 mb-0">
        <p>
          OtakuRealm does not store any files on our server, we only linked to the
          media which is hosted on third party services.
        </p>
        <p>© OtakuRealm</p>
      </div>
    </footer>
  );
}
