export default function PrankPage() {
  return (
    <div
      style={{
        height: "100vh",
        width: "100vw",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        backgroundColor: "#000",
        color: "#fff",
        textAlign: "center",
        padding: "20px",
      }}
      className="overflow-x-hidden"
    >
      <img
        src="/Luffy_Gear_5.png"
        alt="Gear 5 Luffy Laughing"
        style={{
          maxWidth: "90%",
          maxHeight: "60vh",
          borderRadius: "16px",
          marginBottom: "20px",
          display: "block",
        }}
      />
      <h1 style={{ fontSize: "2rem", marginBottom: "10px" }}>😈 Gotcha!</h1>
      <p style={{ fontSize: "1.2rem", maxWidth: "600px" }}>
        You tried opening developer tools... But Gear 5 Luffy says:{" "}
        <strong>“NO SNEAKING!”</strong> 😂
      </p>
    </div>
  );
}
