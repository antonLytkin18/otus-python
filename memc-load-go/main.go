package main

import (
	"appsinstalled"
	"bufio"
	"compress/gzip"
	"errors"
	"flag"
	"fmt"
	"github.com/bradfitz/gomemcache/memcache"
	"github.com/golang/protobuf/proto"
	"log"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"
)

const NormalErrRate = 0.01

type Config struct {
	workers        int
	bufferSize     int
	pattern        string
	maxTries       int
	memcTimeout    int
	memcAddressMap map[string]string
}

type AppsInstalled struct {
	dev_type string
	dev_id   string
	lat      float64
	long     float64
	apps     []uint32
}

type Stat struct {
	total  int
	errors int
}

func (pr *Stat) GetErrorRate() float64 {
	if float64(pr.total) == 0 {
		return 0
	}
	return float64(pr.errors) / float64(pr.total)
}

func (pr *Stat) GetProcessedCount() int {
	return pr.total
}

func (pr *Stat) Add(v *Stat) {
	pr.total += v.total
	pr.errors += v.errors
}

func getFileNames(pattern string) []string {
	files, err := filepath.Glob(pattern)
	if err != nil {
		log.Fatalf("Cannot process files: %s %s\n", pattern, err)
	}
	return files
}

func processFile(fileName string, linesChan chan string) {
	log.Printf("Processing file: %s \n", fileName)
	file, err := os.Open(fileName)
	if err != nil {
		log.Printf("Unable to open file: %s, %s", fileName, err)
		return
	}
	defer file.Close()
	gz, err := gzip.NewReader(file)
	if err != nil {
		log.Printf("Unable to read file: %s, %s", fileName, err)
		return
	}

	defer gz.Close()
	scanner := bufio.NewScanner(gz)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line != "" {
			linesChan <- line
		}
	}
}

func parseAppsWorker(linesChan chan string, appsInstalledChanMap map[string]chan *AppsInstalled, resultsChan chan *Stat) {
	stat := &Stat{}
	for line := range linesChan {
		stat.total += 1
		appsInstalled, err := parseAppsInstalled(line)
		if err != nil {
			stat.errors += 1
			continue
		}
		appsInstalledChan := appsInstalledChanMap[appsInstalled.dev_type]
		if appsInstalledChan == nil {
			stat.errors += 1
			continue
		}
		appsInstalledChan <- appsInstalled
	}
	resultsChan <- stat
}

func insertAppsWorker(memcClient *memcache.Client, maxTries int, appsInstalledChan chan *AppsInstalled, resultsChan chan *Stat) {
	stat := &Stat{}
	for appInstalled := range appsInstalledChan {
		isSuccess := insertAppInstalled(appInstalled, memcClient, maxTries)
		if !isSuccess {
			stat.errors += 1
		}
	}
	resultsChan <- stat
}

func parseAppsInstalled(line string) (*AppsInstalled, error) {
	lineParts := strings.Split(line, "\t")
	if len(lineParts) < 5 {
		return nil, errors.New("unable to parse line. Parts count is more than expected")
	}

	lat, err := strconv.ParseFloat(lineParts[2], 64)
	if err != nil {
		return nil, err
	}
	long, err := strconv.ParseFloat(lineParts[3], 64)
	if err != nil {
		return nil, err
	}
	apps := make([]uint32, 0)
	for _, app := range strings.Split(lineParts[4], ",") {
		appId, _ := strconv.Atoi(app)
		apps = append(apps, uint32(appId))
	}
	return &AppsInstalled{
		dev_type: lineParts[0],
		dev_id:   lineParts[1],
		lat:      lat,
		long:     long,
		apps:     apps,
	}, nil
}

func insertAppInstalled(appsInstalled *AppsInstalled, memcClient *memcache.Client, maxTries int) bool {
	ua := &appsinstalled.UserApps{
		Lat:  proto.Float64(appsInstalled.lat),
		Lon:  proto.Float64(appsInstalled.long),
		Apps: appsInstalled.apps,
	}
	key := fmt.Sprintf("%s:%s", appsInstalled.dev_type, appsInstalled.dev_id)
	packed, err := proto.Marshal(ua)
	if err != nil {
		log.Printf("Unable to create protobuf message: %s", err)
		return false
	}
	attempt := 0
	for maxTries > attempt {
		err = memcClient.Set(&memcache.Item{
			Key:   key,
			Value: packed,
		})
		if err == nil {
			break
		}
		attempt++
		time.Sleep(time.Duration(attempt*100) * time.Millisecond)
	}

	if err != nil {
		log.Printf("Cannot write to memcache: %s", err)
		return false
	}
	return true
}

func dotRename(path string) {
	head := filepath.Dir(path)
	fn := filepath.Base(path)
	if err := os.Rename(path, filepath.Join(head, "."+fn)); err != nil {
		log.Printf("Can't rename a file: %s", path)
		return
	}
	return
}

func printResult(result *Stat) {
	if result.GetErrorRate() > NormalErrRate {
		log.Printf("High error rate (%v > %v). Failed load\n", result.GetErrorRate(), NormalErrRate)
	} else {
		log.Printf("Acceptable error rate (%v). Successful load", result.GetErrorRate())
	}
	log.Printf("Processed count: %v", result.GetProcessedCount())
}

func createConfig() *Config {
	return &Config{
		workers:     workers,
		bufferSize:  bufferSize,
		pattern:     pattern,
		maxTries:    maxTries,
		memcTimeout: timeout,
		memcAddressMap: map[string]string{
			"idfa": idfa,
			"gaid": gaid,
			"adid": adid,
			"dvid": dvid,
		},
	}
}

func getMemcClient(address string, timeout int) *memcache.Client {
	client := memcache.New(address)
	client.Timeout = time.Duration(timeout) * time.Second
	return client
}

func run(config *Config) {
	linesChan := make(chan string, config.bufferSize)
	appsInstalledChanMap := make(map[string]chan *AppsInstalled)
	resultsChan := make(chan *Stat)

	for i := 0; i < config.workers; i++ {
		go parseAppsWorker(linesChan, appsInstalledChanMap, resultsChan)
	}

	for deviceType, memcAddress := range config.memcAddressMap {
		appsInstalledChanMap[deviceType] = make(chan *AppsInstalled)
		memcClient := getMemcClient(memcAddress, config.memcTimeout)
		go insertAppsWorker(memcClient, config.maxTries, appsInstalledChanMap[deviceType], resultsChan)
	}

	fileNames := getFileNames(config.pattern)

	wg := sync.WaitGroup{}
	for _, fileName := range fileNames {
		wg.Add(1)
		go func(fileName string) {
			defer wg.Done()
			processFile(fileName, linesChan)
		}(fileName)
	}

	wg.Wait()
	close(linesChan)

	for _, fileName := range fileNames {
		dotRename(fileName)
	}

	result := &Stat{}
	for i := 0; i < config.workers; i++ {
		result.Add(<-resultsChan)
	}

	for _, appsInstalledChan := range appsInstalledChanMap {
		close(appsInstalledChan)
		result.Add(<-resultsChan)
	}

	printResult(result)
}

var (
	workers    int
	bufferSize int
	pattern    string
	maxTries   int
	timeout    int
	idfa       string
	gaid       string
	adid       string
	dvid       string
)

func init() {
	flag.IntVar(&workers, "workers", 10, "number of insert workers")
	flag.IntVar(&bufferSize, "buffer-size", 10, "buffer size")
	flag.StringVar(&pattern, "pattern", "data/[^.]*.tsv.gz", "filename pattern to parse from")
	flag.IntVar(&maxTries, "max-tries", 3, "max tries")
	flag.IntVar(&timeout, "memc-timeout", 10, "memcache timeout")
	flag.StringVar(&idfa, "idfa", "127.0.0.1:33013", "idfa devices address")
	flag.StringVar(&gaid, "gaid", "127.0.0.1:33014", "gaid devices address")
	flag.StringVar(&adid, "adid", "127.0.0.1:33015", "adid devices address")
	flag.StringVar(&dvid, "dvid", "127.0.0.1:33016", "dvid devices address")
}

func main() {
	flag.Parse()
	run(createConfig())
}
