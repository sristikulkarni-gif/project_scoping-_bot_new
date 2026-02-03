const sharp = require("sharp");
const fs = require("fs");

const inputFile = process.argv[2];
const outputFile = process.argv[3];

if (!inputFile || !outputFile) {
    console.error("Usage: node convert_svg.js <input.svg> <output.png>");
    process.exit(1);
}

try {
    let svgContent = fs.readFileSync(inputFile, "utf8");

    // Graphviz adds physical units (pt) to width/height which can confuse Sharp/librsvg
    // We remove them to force reliance on viewBox, ensuring correct scaling.
    svgContent = svgContent.replace(/<svg([^>]*)width="[^"]*"([^>]*)>/, '<svg$1$2>');
    svgContent = svgContent.replace(/<svg([^>]*)height="[^"]*"([^>]*)>/, '<svg$1$2>');

    // Use a reasonable density (96 DPI is standard for screen, 300 for print). 
    // Since we stripped physical units, density applies to the viewBox user units if they are small.
    // However, Graphviz viewBox is usually in points/pixels. 
    // Let's try density 96 first to match standard screen rendering, or just rely on resizing if needed.
    // Actually, setting density=150 gives a good balance.

    sharp(Buffer.from(svgContent), { density: 150 })
        .png()
        .toFile(outputFile)
        .then(() => {
            console.log("Conversion successful");
        })
        .catch((err) => {
            console.error("Conversion failed:", err);
            process.exit(1);
        });
} catch (err) {
    console.error("File read failed:", err);
    process.exit(1);
}
