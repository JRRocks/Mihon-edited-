package mihon.feature.colorization

import io.kotest.matchers.collections.shouldHaveSize
import io.kotest.matchers.shouldBe
import org.junit.jupiter.api.Test
import kotlin.math.abs

class ColorizationPipelineTest {

    private fun gray(v: Int) = ColorizationPipeline.argb(v, v, v)

    @Test
    fun `luminance composites transparency onto white`() {
        ColorizationPipeline.luminance(gray(0)) shouldBe 0
        ColorizationPipeline.luminance(gray(255)) shouldBe 255
        ColorizationPipeline.luminance(0x00000000) shouldBe 255
        ColorizationPipeline.luminance(ColorizationPipeline.argb(255, 0, 0)) shouldBe 76
    }

    @Test
    fun `content size keeps the aspect ratio`() {
        ColorizationPipeline.contentSize(1000, 1500, 576) shouldBe (384 to 576)
        ColorizationPipeline.contentSize(1500, 1000, 576) shouldBe (576 to 384)
        ColorizationPipeline.contentSize(200, 300, 576) shouldBe (384 to 576)
    }

    @Test
    fun `area resize averages the covered pixels`() {
        val src = floatArrayOf(
            0f, 2f, 10f, 10f,
            4f, 6f, 10f, 10f,
            1f, 1f, 3f, 3f,
            1f, 1f, 3f, 3f,
        )
        val dst = ColorizationPipeline.resizeArea(src, 4, 4, 2, 2)
        dst.toList() shouldBe listOf(3f, 10f, 1f, 3f)
    }

    @Test
    fun `area resize keeps a flat image flat for any ratio`() {
        val src = FloatArray(37 * 53) { 0.5f }
        val dst = ColorizationPipeline.resizeArea(src, 37, 53, 11, 29)
        dst.all { abs(it - 0.5f) < 1e-5f } shouldBe true
    }

    @Test
    fun `input tensor is padded with white and has empty hint channels`() {
        val tensor = ColorizationPipeline.buildInputTensor(FloatArray(40 * 33) { 0.25f }, 40, 33)
        val width = 64
        val height = 64
        tensor shouldHaveSize 5 * width * height
        tensor[0] shouldBe 0.25f
        tensor[39] shouldBe 0.25f
        tensor[40] shouldBe 1f
        tensor[33 * width] shouldBe 1f
        tensor.drop(width * height).all { it == 0f } shouldBe true
    }

    @Test
    fun `output is mapped to bytes and cropped`() {
        val plane = 32 * 32
        val output = FloatArray(3 * plane)
        for (i in 0 until plane) {
            output[i] = 1f
            output[plane + i] = -1f
            output[2 * plane + i] = 0f
        }
        val pixels = ColorizationPipeline.decodeOutput(output, 32, 32, 20, 10)
        pixels shouldHaveSize 200
        pixels.all { it == ColorizationPipeline.argb(255, 0, 128) } shouldBe true
    }

    @Test
    fun `ink retention keeps line art and applies the predicted colors`() {
        val width = 8
        val height = 8
        // White page with a black line
        val pixels = IntArray(width * height) { if (it % width == 3) gray(0) else gray(255) }
        val low = FloatArray(4 * 4) { 1f }
        val prediction = IntArray(4 * 4) { ColorizationPipeline.argb(200, 100, 50) }
        ColorizationPipeline.retainInk(pixels, width, height, low, prediction, 4, 4)

        pixels[3] shouldBe gray(0)
        pixels[0] shouldBe ColorizationPipeline.argb(200, 100, 50)
    }

    @Test
    fun `regular pages are colorized in one piece`() {
        ColorizationPipeline.tiles(1000, 1500) shouldBe listOf(ColorizationPipeline.Tile(0, 0, 1000, 1500))
    }

    @Test
    fun `long strips are split into parts covering the whole page`() {
        val tiles = ColorizationPipeline.tiles(800, 10000)
        tiles.size shouldBe 9
        tiles.first().top shouldBe 0
        tiles.zipWithNext().all { (a, b) -> a.top + a.height == b.top } shouldBe true
        tiles.last().let { it.top + it.height } shouldBe 10000
        tiles.all { it.width == 800 } shouldBe true
    }

    @Test
    fun `color pages are detected`() {
        val grayscale = IntArray(10000) { gray(it % 256) }
        ColorizationPipeline.isAlreadyColored(grayscale) shouldBe false

        val colored = IntArray(10000) { if (it % 4 == 0) ColorizationPipeline.argb(220, 40, 40) else gray(255) }
        ColorizationPipeline.isAlreadyColored(colored) shouldBe true
    }
}
