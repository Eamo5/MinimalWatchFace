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
        versionCode = libs.versions.versionCode.get().toInt()
        versionName = libs.versions.versionName.get()
    }

    productFlavors {
        flavorDimensions.add("version")
        create("wear4") {
            dimension = "version"
            manifestPlaceholders["wffVersion"] = "1"
            minSdk = 33
            versionName = "${libs.versions.versionName.get()}-4"
        }
        create("wear5") {
            dimension = "version"
            manifestPlaceholders["wffVersion"] = "2"
            minSdk = 34
            versionName = "${libs.versions.versionName.get()}-5"
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

tasks.register("validateWffXml") {
    val relativeDir = "../watchface-tools/third_party/wff"
    val buildTask = ":specification:validator:build"
    val jarFile = file(
        "$relativeDir/specification/validator/build/libs/dwf-format-2-validator-1.0.jar"
    )

    val fileToWffVersion = mapOf (
        1 to file("src/wear4/res/raw/watchface.xml"),
        2 to file("src/wear5/res/raw/watchface.xml")
    )

    doLast {
        // Validate that the relative directory exists
        val relativeDirFile = file(relativeDir)
        if (!relativeDirFile.exists() || !relativeDirFile.isDirectory) {
            throw GradleException(
                "The specified relative directory does not exist: $relativeDirFile"
            )
        }

        // Run the build task in the relative directory
        println("Running Gradle build task in $relativeDirFile...")
        exec {
            workingDir = relativeDirFile
            // Detect the platform-specific gradlew script
            val gradlewScript =
                if (System.getProperty("os.name").lowercase().contains("win")) {
                    "gradlew.bat"
                } else {
                    "./gradlew"
                }
            commandLine(gradlewScript, buildTask)
        }

        // Validate that the JAR file exists
        if (!jarFile.exists()) {
            throw GradleException("JAR file not found at ${jarFile.absolutePath}")
        }

        // Validate that the input file exists
        fileToWffVersion.forEach {
            if (!it.value.exists()) {
                throw GradleException("Input file not found at ${it.value.absolutePath}")
            }

            val validatorArgs = listOf(it.key, it.value.absolutePath)

            // Run the resulting JAR file
            try {
                println("Running JAR file $jarFile with arguments: $validatorArgs")
                exec {
                    commandLine(
                        "java", "-jar", jarFile.absolutePath, *validatorArgs.toTypedArray()
                    )
                }
            } catch (e: ExecException) {
                throw GradleException("The JAR execution failed: ${e.message}. " +
                        "Check the JAR's output for more details.")
            }
        }

    }
}

tasks.register("validateMemoryFootprint") {
    // Define the build variant dynamically
    val buildVariant = project.gradle.startParameter.taskNames
        .find { it.contains("Debug", ignoreCase = true) }?.let { "debug" }
        ?: project.gradle.startParameter.taskNames
            .find { it.contains("Release", ignoreCase = true) }?.let { "release" }

    val buildFlavor = project.gradle.startParameter.taskNames
        .find { it.contains("wear5", ignoreCase = true) }?.let { "wear5" }
        ?: project.gradle.startParameter.taskNames
            .find { it.contains("wear4", ignoreCase = true) }?.let { "wear4" }

    val relativeDirPath = "../watchface-tools/play-validations"
    val buildTask = ":memory-footprint:jar"
    val jarFile = file("$relativeDirPath/memory-footprint/build/libs/memory-footprint.jar")

    val apks = if (buildFlavor != null && buildVariant != null) {
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
    val schemaVersion = 2
    val ambientLimitMb = 10
    val activeLimitMb = 100
    val additionalArgs = listOf("--apply-v1-offload-limitations", "--estimate-optimization")

    doLast {
        val relativeDir = file(relativeDirPath)
        // Validate that the relative directory exists
        if (!relativeDir.exists() || !relativeDir.isDirectory) {
            throw GradleException("The specified relative directory does not exist: $relativeDir")
        }

        // Run the build task in the relative directory
        println("Running Gradle build task in $relativeDir...")
        exec {
            workingDir = relativeDir
            // Detect the platform-specific gradlew script
            val gradlewScript =
                if (System.getProperty("os.name").lowercase().contains("win")) {
                    "gradlew.bat"
                } else {
                    "./gradlew"
                }
            commandLine(gradlewScript, buildTask)
        }

        // Validate that the JAR file exists
        if (!jarFile.exists()) {
            throw GradleException("JAR file not found at ${jarFile.absolutePath}")
        }

        var apkFound = false

        apks.forEach {
            if (it.exists()) {
                apkFound = true
            } else {
                return@forEach
            }

            try {
                // Run the resulting JAR file
                println("Running JAR file $jarFile with arguments for APK: ${it.absolutePath}")
                exec {
                    commandLine(
                        "java", "-jar", jarFile.absolutePath,
                        "--watch-face", it.absolutePath,
                        "--schema-version", schemaVersion.toString(),
                        "--ambient-limit-mb", ambientLimitMb.toString(),
                        "--active-limit-mb", activeLimitMb.toString(),
                        *additionalArgs.toTypedArray()
                    )
                }
            } catch (e: ExecException) {
                throw GradleException(
                    "The JAR execution failed with an error: ${e.message}. " +
                            "Please check the JAR's output for more details."
                )
            }
        }
        if (!apkFound) {
            throw GradleException("No valid APK files found")
        }
    }
}

tasks.register("optimizeWff") {
    val buildVariant = project.gradle.startParameter.taskNames
        .find { it.contains("Debug", ignoreCase = true) }?.let { "debug" }
        ?: project.gradle.startParameter.taskNames
            .find { it.contains("Release", ignoreCase = true) }?.let { "release" }

    if (buildVariant.equals("release")) {
        throw GradleException("Release builds cannot be optimized due to obfuscation. " +
                "Please optimize a debug build instead.")
    }

    val buildFlavor = project.gradle.startParameter.taskNames
        .find { it.contains("wear5", ignoreCase = true) }?.let { "wear5" }
        ?: project.gradle.startParameter.taskNames
            .find { it.contains("wear4", ignoreCase = true) }?.let { "wear4" }

    val relativeDir = "../watchface-tools/tools"
    val buildTask = ":wff-optimizer:jar"
    val jarFile = file("$relativeDir/wff-optimizer/build/libs/wff-optimizer.jar")
    val wear4 = "wear4"
    val wear5 = "wear5"

    val apks = buildFlavor?.let {
       // Test active build flavor
       mapOf(
           buildFlavor to
                   file("build/outputs/apk/$buildFlavor/debug/watchface-$buildFlavor-debug.apk")
       )
    } ?: mapOf(
       wear4 to file("build/outputs/apk/wear4/debug/watchface-wear4-debug.apk"),
       wear4 to file("build/intermediates/apk/wear4/debug/watchface-wear4-debug.apk"),
       wear5 to file("build/outputs/apk/wear5/debug/watchface-wear5-debug.apk"),
       wear5 to file("build/intermediates/apk/wear5/debug/watchface-wear5-debug.apk")
    )

    // Ensure the unzipDir path is properly constructed
    val unzipDir = file(layout.buildDirectory.dir("intermediates/unzipped_apk"))
    val optimizedWffPath = unzipDir.resolve("res/raw/watchface.xml")

    doLast {
        // Validate relative directory exists
        val relativeDirFile = file(relativeDir)
        if (!relativeDirFile.exists() || !relativeDirFile.isDirectory) {
            throw GradleException("The specified relative directory does not exist: $relativeDir")
        }

        // Run the Gradle build task to generate the JAR file
        exec {
            workingDir = relativeDirFile
            // Detect the platform-specific gradlew script
            val gradlewScript =
                if (System.getProperty("os.name").lowercase().contains("win")) {
                    "gradlew.bat"
                } else {
                    "./gradlew"
                }
            commandLine(gradlewScript, buildTask)
        }

        // Validate the JAR file exists
        if (!jarFile.exists()) {
            throw GradleException("JAR file not found at ${jarFile.absolutePath}")
        }

        var apkFound = false
        apks.forEach {
            if (it.value.exists()) {
                apkFound = true
            } else {
                return@forEach
            }

            // Create a temp directory in intermediates for unzipping the APK
            if (unzipDir.exists()) {
                unzipDir.deleteRecursively()
            }
            unzipDir.mkdirs()

            // Use Gradle to unzip APK
            copy {
                from(zipTree(it.key))
                into(unzipDir)
            }

            // Execute WFF optimizer
            try {
                // Run the resulting JAR file
                println("Running JAR file $jarFile with arguments for APK: ${it.value.absolutePath}")
                exec {
                    commandLine("java", "-jar", jarFile.absolutePath, "--source", unzipDir)
                }
            } catch (e: ExecException) {
                throw GradleException(
                    "The JAR execution failed with an error: ${e.message}. " +
                            "Please check the JAR's output for more details."
                )
            }

            // Copy WFF file into src if exists
            if (optimizedWffPath.exists()) {
                copy {
                    from(optimizedWffPath)
                    into("src/${it.key}/res/raw")
                }
            } else {
                throw GradleException("Optimized WFF not found at $optimizedWffPath")
            }
        }
        if (!apkFound) {
            throw GradleException("No valid APK files found")
        }
    }
}
