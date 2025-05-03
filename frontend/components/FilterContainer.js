import React, { useState, useEffect } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faSearch, faChevronDown } from "@fortawesome/free-solid-svg-icons";
import { useSearchParams, useRouter } from "next/navigation";

const filters = [
  {
    filter: "Type",
    id: "type",
    options: [
      { name: "Movie", value: "Movie" },
      { name: "Music", value: "Music" },
      { name: "ONA", value: "ONA" },
      { name: "OVA", value: "OVA" },
      { name: "Special", value: "Special" },
      { name: "TV", value: "TV" },
    ],
  },
  {
    filter: "Genres",
    id: "genres",
    options: [
      { name: "Action", value: "1" },
      { name: "Adventure", value: "2" },
      { name: "Cars", value: "538" },
      { name: "Comedy", value: "8" },
      { name: "Dementia", value: "453" },
      { name: "Demons", value: "119" },
      { name: "Drama", value: "62" },
      { name: "Ecchi", value: "214" },
      { name: "Fantasy", value: "3" },
      { name: "Game", value: "180" },
      { name: "Harem", value: "215" },
      { name: "Historical", value: "70" },
      { name: "Horror", value: "222" },
      { name: "Isekai", value: "74" },
      { name: "Josei", value: "404" },
      { name: "Kids", value: "46" },
      { name: "Magic", value: "203" },
      { name: "Martial Arts", value: "114" },
      { name: "Mecha", value: "123" },
      { name: "Military", value: "125" },
      { name: "Music", value: "242" },
      { name: "Mystery", value: "57" },
      { name: "Parody", value: "162" },
      { name: "Police", value: "136" },
      { name: "Psychological", value: "73" },
      { name: "Romance", value: "28" },
      { name: "Samurai", value: "163" },
      { name: "School", value: "14" },
      { name: "Sci-Fi", value: "12" },
      { name: "Seinen", value: "50" },
      { name: "Shoujo", value: "252" },
      { name: "Shoujo Ai", value: "235" },
      { name: "Shounen", value: "15" },
      { name: "Shounen Ai", value: "233" },
      { name: "Slice of Life", value: "35" },
      { name: "Space", value: "124" },
      { name: "Sports", value: "29" },
      { name: "Super Power", value: "16" },
      { name: "Supernatural", value: "9" },
      { name: "Thriller", value: "54" },
      { name: "unknown", value: "32" },
      { name: "Vampire", value: "58" },
    ],
  },
  {
    filter: "Year",
    id: "year",
    options: Array.from({ length: 2025 - 1980 + 1 }, (_, i) => {
      const year = 2025 - i;
      return { name: String(year), value: String(year) };
    }),
  },
  {
    filter: "Rating",
    id: "rating",
    options: [
      { name: "G - All Ages", value: "g" },
      { name: "PG - Children", value: "pg" },
      { name: "PG 13 - Teens", value: "pg_13" },
      { name: "R - 17+", value: "r" },
      { name: "R+ - Mild Nudity", value: "r+" },
      { name: "Rx - Hentai", value: "rx" },
    ],
  },
  {
    filter: "Status",
    id: "status",
    options: [
      { name: "Finished Airing", value: "finished-airing" },
      { name: "Currently Airing", value: "currently-airing" },
      { name: "Not Yet Aired", value: "not-yet-aired" },
    ],
  },
  {
    filter: "Season",
    id: "season",
    options: [
      { name: "Spring", value: "spring" },
      { name: "Summer", value: "summer" },
      { name: "Fall", value: "fall" },
      { name: "Winter", value: "winter" },
    ],
  },
  {
    filter: "Language",
    id: "language",
    options: [
      { name: "Sub", value: "sub" },
      { name: "Dub", value: "dub" },
    ],
  },
  {
    filter: "Default",
    id: "default",
    options: [
      { name: "Default", value: "default" },
      { name: "Latest Updated", value: "latest-updated" },
      { name: "Score", value: "score" },
      { name: "Name A-Z", value: "name-az" },
      { name: "Release Date", value: "release-date" },
      { name: "Most Viewed", value: "most-viewed" },
    ],
  },
];

export default function FilterContainer() {
  const [openDropdown, setOpenDropdown] = useState(null);
  const [selected, setSelected] = useState({});

  const searchParams = useSearchParams();
  const router = useRouter(); 
  
  const keyword = searchParams.get("keyword") || "";

  const [animeTitle, setAnimeTitle] = useState(keyword);

  useEffect(() => {
    setAnimeTitle(keyword);
  }, [keyword]);

  const toggleDropdown = (id) => {
    setOpenDropdown((prev) => (prev === id ? null : id));
  };

  const handleSelect = (filterId, value, isMulti) => {
    setSelected((prev) => {
      if (isMulti) {
        const current = prev[filterId] || [];
        return {
          ...prev,
          [filterId]: current.includes(value)
            ? current.filter((v) => v !== value)
            : [...current, value],
        };
      } else {
        return { ...prev, [filterId]: value };
      }
    });

    if (!isMulti) setOpenDropdown(null);
  };

  const isMultiSelect = (id, index) => {
    // Make last one radio, rest checkboxes
    const isLast = index === filters.length - 1;
    return !isLast;
  };

   // 🔑 Build the query string
   const buildQuery = () => {
    const params = new URLSearchParams();

    // Anime title
    params.append("keyword", animeTitle);

    // Map your filters to query keys
    const mapping = {
      type: "term_type[]",
      genres: "genre[]",
      country: "country",
      sort: "sort",
      year: "year",
      rating: "rating",
      status: "status",
      season: "season",
      language: "language",
    };

    // Loop through selected filters
    Object.entries(selected).forEach(([key, value]) => {
      const paramKey = mapping[key];
      if (!paramKey) return; // skip unknowns

      if (Array.isArray(value)) {
        value.forEach((val) => {
          const opt = filters
            .find((f) => f.id === key)
            ?.options.find((o) => o.name === val);
          if (opt) {
            params.append(paramKey, opt.value);
          }
        });
      } else {
        const opt = filters
          .find((f) => f.id === key)
          ?.options.find((o) => o.name === value);
        if (opt) {
          params.append(paramKey, opt.value);
        } else {
          // fallback for things like 'sort' which can be a string
          params.append(paramKey, value);
        }
      }
    });

    // Add missing params if needed
    if (!params.has("type")) params.append("type", "");
    if (!params.has("country")) params.append("country", "");
    if (!params.has("sort")) params.append("sort", "default");

    return `/filter?${params.toString()}`;
  };

  return (
    <div className="p-5 pl-4 sm:pl-10 lg:pl-20 pr-4 sm:pr-10 lg:pr-32 mt-10">
      <h2 className="text-2xl font-bold mb-4 text-[#bb5052] uppercase">
        Filter
      </h2>

      <div className="grid gap-3 text-[#505050] sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5">
        {/* Anime Title */}
        <div className="bg-[#191919] p-2 hover:bg-[#303030] flex items-center gap-2 col-span-full lg:col-span-1">
          <FontAwesomeIcon icon={faSearch} />
          <input
            type="text"
            placeholder="Anime Title"
            value={animeTitle}
            onChange={(e) => setAnimeTitle(e.target.value)}
            className="bg-transparent outline-none w-full text-white"
          />
        </div>

        {/* Dynamic Dropdowns */}
        {filters.map(({ filter, id, options }, index) => {
          const multi = isMultiSelect(id, index);
          const selectedValues = multi
            ? Array.isArray(selected[id])
              ? selected[id]
              : []
            : selected[id] || "";

          // Determine grid columns based on filter id
          let gridCols = "grid-cols-1";
          if (id === "genres") {
            gridCols = gridCols =
              "grid-cols-2 sm:grid-cols-31md:grid-cols-2 xl:grid-cols-4";
          } else if (id === "year") {
            gridCols =
              "grid-cols-2 sm:grid-cols-1 md:grid-cols-2 xl:grid-cols-3";
          }

          return (
            <div
              key={id}
              className="relative bg-[#191919] text-white p-2 hover:bg-[#303030] cursor-pointer"
              onClick={() => toggleDropdown(id)}
            >
              <div className="flex justify-between items-center">
                <span className="truncate">
                  {multi
                    ? selectedValues.length > 0
                      ? selectedValues.join(", ")
                      : filter
                    : selectedValues || filter}
                </span>
                <FontAwesomeIcon icon={faChevronDown} />
              </div>

              {/* Dropdown Menu */}
              {openDropdown === id && (
                <div className="absolute z-10 top-full left-0 mt-1 bg-[#252525] border border-[#444] rounded shadow-lg max-h-60 overflow-y-auto w-[500px] min-w-[200px] p-2">
                  <div className={`grid gap-2 ${gridCols}`}>
                    {options.map((opt) => {
                      const isChecked = multi
                        ? selectedValues.includes(opt.name)
                        : selectedValues === opt.name;
                      return (
                        <label
                          key={opt.value}
                          className="flex items-center gap-2 text-sm px-2 py-1 hover:bg-[#404040] rounded cursor-pointer"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <input
                            type={multi ? "checkbox" : "radio"}
                            name={id}
                            value={opt.value}
                            checked={isChecked}
                            onChange={() => handleSelect(id, opt.name, multi)}
                            className="accent-[#bb5052] w-4 h-4 rounded-sm border border-[#555]"
                          />
                          {opt.name}
                        </label>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {/* Filter Button */}
        <div
          className="bg-[#353535] p-2 hover:bg-[#505050] text-white text-center text-base tracking-[1.5px] col-span-full sm:col-span-1"
          onClick={() => {
            const url = buildQuery();
            router.push(url);
          }}
        >
          <button>Filter</button>
        </div>
      </div>
    </div>
  );
}
