import org.gradle.process.internal.ExecException

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
}

android {
    namespace = "com.eamo5.minimalwatchface"
    compileSdk = libs.versions.compileSdk.get().toInt()

    defaultConfig {
        applicationId = "com.eamo5.minimalwatchface"
        minSdk = libs.versions.minSdk.get().toInt()
        targetSdk = libs.versions.targetSdk.get().toInt()
        versionName = libs.versions.versionName.get()
    }

    productFlavors {
        flavorDimensions.add("sdk")
        create("wear4") {
            dimension = "sdk"
            manifestPlaceholders["wffVersion"] = "1"
            minSdk = 33
            versionCode = libs.versions.wear4VersionCode.get().toInt()
        }
        create("wear5") {
            dimension = "sdk"
            manifestPlaceholders["wffVersion"] = "2"
            minSdk = 34
            versionCode = libs.versions.wear5VersionCode.get().toInt()
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}

abstract class ValidateWffXmlTask @Inject constructor(
    private val execOps: ExecOperations,
) : DefaultTask() {
    @get:InputDirectory
    @get:PathSensitive(PathSensitivity.RELATIVE)
    lateinit var validatorDir: File

    @get:Input
    lateinit var gradleBuildTask: String

    @get:OutputFile
    lateinit var jarFile: File

    @get:Internal
    lateinit var versionedWffFiles: Map<Int, File>

    @get:Input
    lateinit var gradlewScript: String

    @TaskAction
    fun run() {
        if (!validatorDir.exists() || !validatorDir.isDirectory) {
            throw GradleException("The specified relative directory does not exist: $validatorDir")
        }
        println("Running Gradle build task in $validatorDir...")
        execOps.exec {
            workingDir(validatorDir)
            commandLine(gradlewScript, gradleBuildTask)
        }
        if (!jarFile.exists()) {
            // Attempt dynamic resolution of jar files
            val libsDir = File(validatorDir, "specification/validator/build/libs")
            if (libsDir.exists()) {
                val candidate = libsDir.listFiles()?.firstOrNull { f ->
                    f.isFile && f.name.startsWith("wff-validator") && f.extension == "jar"
                }
                if (candidate != null) {
                    println("Discovered validator jar: ${candidate.name}")
                    jarFile = candidate
                }
            }
        }
        if (!jarFile.exists()) {
            throw GradleException("Validator JAR file not found (looked for ${jarFile.absolutePath})")
        }
        versionedWffFiles.forEach { (version, wffFile) ->
            if (!wffFile.exists()) {
                throw GradleException("Input file not found at ${wffFile.absolutePath}")
            }
            val validatorArgs = listOf(version.toString(), wffFile.absolutePath)
            try {
                println("Running JAR file $jarFile with arguments: $validatorArgs")
                execOps.exec {
                    commandLine("java",
                        "-jar",
                        jarFile.absolutePath,
                        *validatorArgs.toTypedArray()
                    )
                }
            } catch (e: ExecException) {
                throw GradleException(
                    "The JAR execution failed: ${e.message}."
                            + "Check the JAR's output for more details."
                )
            }
        }
    }
}

abstract class ValidateMemoryFootprintTask @Inject constructor(
    private val execOps: ExecOperations,
) : DefaultTask() {
    @get:InputDirectory
    @get:PathSensitive(PathSensitivity.RELATIVE)
    lateinit var relativeDir: File

    @get:Input
    lateinit var gradlewScript: String

    @get:Input
    lateinit var gradleBuildTask: String

    @get:OutputFile
    lateinit var jarFile: File

    @get:InputFiles
    @get:Optional
    @get:PathSensitive(PathSensitivity.RELATIVE)
    var apks: List<File> = emptyList()

    @get:Input
    val schemaVersion = 4

    @get:Input
    val ambientLimitMb = 10

    @get:Input
    val activeLimitMb = 100

    @get:Input
    var additionalArgs: List<String> = emptyList()

    @TaskAction
    fun run() {
        if (!relativeDir.exists() || !relativeDir.isDirectory) {
            throw GradleException("The specified relative directory does not exist: $relativeDir")
        }
        println("Running Gradle build task in $relativeDir...")
        execOps.exec { workingDir(relativeDir); commandLine(gradlewScript, gradleBuildTask) }
        if (!jarFile.exists()) {
            // Attempt dynamic resolution of jar files
            val libsDir = File(relativeDir, "memory-footprint/build/libs")
            if (libsDir.exists()) {
                val all = libsDir.listFiles()?.filter { f -> f.isFile && f.name.startsWith("memory-footprint") && f.extension == "jar" } ?: emptyList()
                val newest = all.maxByOrNull { it.lastModified() }
                if (newest != null) {
                    println("Using discovered memory-footprint jar: ${newest.name}")
                    jarFile = newest
                } else {
                    println("No memory-footprint*.jar files found in ${libsDir.absolutePath}")
                }
            } else {
                println("Libs directory not found: ${libsDir.absolutePath}")
            }
        }
        if (!jarFile.exists()) throw GradleException("Memory-footprint JAR file not found (looked for ${jarFile.absolutePath})")
        var apkFound = false
        apks.forEach { apk ->
            if (!apk.exists()) return@forEach
            apkFound = true
            try {
                println("Running JAR file $jarFile with arguments for APK: ${apk.absolutePath}")
                execOps.exec {
                    commandLine(
                        "java", "-jar", jarFile.absolutePath,
                        "--watch-face", apk.absolutePath,
                        "--schema-version", schemaVersion.toString(),
                        "--ambient-limit-mb", ambientLimitMb.toString(),
                        "--active-limit-mb", activeLimitMb.toString(),
                        *additionalArgs.toTypedArray()
                    )
                }
            } catch (e: ExecException) {
                throw GradleException(
                    "The JAR execution failed with an error: ${e.message}. "
                            + "Please check the JAR's output for more details."
                )
            }
        }
        if (!apkFound) throw GradleException("No valid APK files found")
    }
}

abstract class OptimizeWffTask @Inject constructor(
    private val execOps: ExecOperations,
    private val archives: ArchiveOperations,
    private val fs: FileSystemOperations,
) : DefaultTask() {
    @get:Input
    lateinit var gradlewScript: String

    @get:Input
    lateinit var gradleBuildTask: String

    @get:InputDirectory
    @get:PathSensitive(PathSensitivity.RELATIVE)
    lateinit var toolDir: File

    @get:OutputFile
    lateinit var jarFile: File

    @get:OutputDirectory
    lateinit var unzipDir: File

    @get:Internal
    lateinit var optimizedWffPath: File

    @get:InputFiles
    @get:Optional
    @get:PathSensitive(PathSensitivity.RELATIVE)
    var apkFiles: List<File> = emptyList()

    @get:Internal
    var candidateApks: Map<String, List<File>> = emptyMap()

    @get:Input
    @get:Optional
    var buildVariant: String? = null

    @TaskAction
    fun run() {
        if (buildVariant == "release") {
            throw GradleException(
                "Release builds cannot be optimized due to obfuscation."
                    +"Please optimize a debug build instead."
            )
        }
        if (!toolDir.exists() || !toolDir.isDirectory) {
            throw GradleException("The specified relative directory does not exist: $toolDir")
        }
        // Unconditionally build the optimizer jar to ensure freshness in CI
        println("Building optimizer jar in $toolDir ...")
        execOps.exec {
            workingDir(toolDir)
            commandLine(gradlewScript, gradleBuildTask)
        }
        if (!jarFile.exists()) {
            throw GradleException("Optimizer JAR file not found at ${jarFile.absolutePath}")
        }
        var apkFound = false
        candidateApks.forEach { (flavor, candidates) ->
            val apk = candidates.firstOrNull { it.exists() } ?: return@forEach
            apkFound = true
            if (unzipDir.exists()) unzipDir.deleteRecursively()
            unzipDir.mkdirs()
            fs.copy { from(archives.zipTree(apk)); into(unzipDir) }
            try {
                println("Running JAR file $jarFile with arguments for APK: ${apk.absolutePath}")
                execOps.exec { commandLine("java", "-jar", jarFile.absolutePath, "--source", unzipDir) }
            } catch (e: ExecException) {
                throw GradleException(
                    "The JAR execution failed with an error: ${e.message}."
                        + "Please check the JAR's output for more details."
                )
            }
            if (optimizedWffPath.exists()) {
                fs.copy { from(optimizedWffPath); into("src/$flavor/res/raw") }
            } else {
                throw GradleException("Optimized WFF not found at $optimizedWffPath")
            }
        }
        if (!apkFound) throw GradleException("No valid APK files found")
    }
}

tasks.register<ValidateWffXmlTask>("validateWffXml") {
    validatorDir = file("../watchface-tools/third_party/wff")
    gradleBuildTask = ":specification:validator:build"
    jarFile = file("../watchface-tools/third_party/wff/specification/validator/build/libs/wff-validator.jar")
    versionedWffFiles = mapOf(
        1 to file("src/wear4/res/raw/watchface.xml"),
        4 to file("src/wear5/res/raw/watchface.xml")
    )
    gradlewScript = if (System.getProperty("os.name").lowercase().contains("win"))
        "gradlew.bat" else "./gradlew"
}

tasks.register<ValidateMemoryFootprintTask>("validateMemoryFootprint") {
    val taskNames = gradle.startParameter.taskNames
    val buildVariant = taskNames.find { it.contains("Debug", true) }?.let { "debug" }
        ?: taskNames.find { it.contains("Release", true) }?.let { "release" }
    val buildFlavor = taskNames.find { it.contains("wear5", true) }?.let { "wear5" }
        ?: taskNames.find { it.contains("wear4", true) }?.let { "wear4" }
    relativeDir = file("../watchface-tools/play-validations")
    gradleBuildTask = ":memory-footprint:build"
    jarFile = file("../watchface-tools/play-validations/memory-footprint/build/libs/memory-footprint.jar")
    apks = if (buildFlavor != null && buildVariant != null) {
        listOf(
            file("build/outputs/apk/$buildFlavor/$buildVariant/watchface-$buildFlavor-$buildVariant.apk"),
            file("build/intermediates/apk/$buildFlavor/$buildVariant/watchface-$buildFlavor-$buildVariant.apk")
        )
    } else {
        listOf(
            file("build/outputs/apk/wear4/debug/watchface-wear4-debug.apk"),
            file("build/intermediates/apk/wear4/debug/watchface-wear4-debug.apk"),
            file("build/outputs/apk/wear4/release/watchface-wear4-release.apk"),
            file("build/intermediates/apk/wear4/release/watchface-wear4-release.apk"),
            file("build/outputs/apk/wear5/debug/watchface-wear5-debug.apk"),
            file("build/intermediates/apk/wear5/debug/watchface-wear5-debug.apk"),
            file("build/outputs/apk/wear5/release/watchface-wear5-release.apk"),
            file("build/intermediates/apk/wear5/release/watchface-wear5-release.apk")
        )
    }
    additionalArgs = listOf("--apply-v1-offload-limitations", "--estimate-optimization")
    gradlewScript = if (System.getProperty("os.name").lowercase().contains("win")) {
        "gradlew.bat"
    } else "./gradlew"
}

tasks.register<OptimizeWffTask>("optimizeWff") {
    val taskNames = gradle.startParameter.taskNames
    buildVariant = taskNames.find { it.contains("Debug", true) }?.let { "debug" }
        ?: taskNames.find { it.contains("Release", true) }?.let { "release" }
    val buildFlavor = taskNames.find { it.contains("wear5", true) }?.let { "wear5" }
        ?: taskNames.find { it.contains("wear4", true) }?.let { "wear4" }
    gradleBuildTask = ":wff-optimizer:jar"
    toolDir = file("../watchface-tools/tools")
    jarFile = file("../watchface-tools/tools/wff-optimizer/build/libs/wff-optimizer.jar")
    val wear4 = "wear4"
    val wear5 = "wear5"
    candidateApks = if (buildFlavor != null) {
        mapOf(buildFlavor to listOf(
            file("build/outputs/apk/$buildFlavor/debug/watchface-$buildFlavor-debug.apk"),
            file("build/intermediates/apk/$buildFlavor/debug/watchface-$buildFlavor-debug.apk"))
        )
    } else {
        mapOf(
            wear4 to listOf(
                file("build/outputs/apk/wear4/debug/watchface-wear4-debug.apk"),
                file("build/intermediates/apk/wear4/debug/watchface-wear4-debug.apk")
            ),
            wear5 to listOf(
                file("build/outputs/apk/wear5/debug/watchface-wear5-debug.apk"),
                file("build/intermediates/apk/wear5/debug/watchface-wear5-debug.apk")
            )
        )
    }
    apkFiles = candidateApks.values.flatten()
    unzipDir = layout.buildDirectory.dir("intermediates/unzipped_apk").get().asFile
    optimizedWffPath = unzipDir.resolve("res/raw/watchface.xml")
    gradlewScript = if (System.getProperty("os.name").lowercase().contains("win"))
        "gradlew.bat" else "./gradlew"
}
